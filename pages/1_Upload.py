import streamlit as st
import pandas as pd
import uuid
import os
from pathlib import Path
from datetime import datetime

from src.db import get_conn

st.title("Upload / Import Phrases")

UPLOAD_DIR = Path("data") / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLS = ["scene", "en"]
OPTIONAL_COLS = ["zh", "tags", "level"]

st.caption("You can upload once, then reuse files from the dropdown next time. (上传一次，以后下拉选择即可)")

# -----------------------------
# Section A: choose an existing saved CSV
# -----------------------------
saved_files = sorted([p.name for p in UPLOAD_DIR.glob("*.csv")], reverse=True)

st.subheader("A) Use an existing file (复用已上传文件)")
selected = st.selectbox("Select a saved CSV", ["(none)"] + saved_files)

df = None
selected_path = None

if selected != "(none)":
    selected_path = UPLOAD_DIR / selected
    try:
        df = pd.read_csv(selected_path)
        st.success(f"Loaded: {selected_path}")
    except Exception as e:
        st.error(f"Failed to read selected CSV: {e}")
        df = None

st.divider()

# -----------------------------
# Section B: upload a new CSV (and save it)
# -----------------------------
st.subheader("B) Upload a new file (上传新文件)")
uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded is not None:
    # Save the uploaded file so you can reuse later
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = uploaded.name.replace(" ", "_")
    saved_name = f"{timestamp}-{safe_name}"
    save_path = UPLOAD_DIR / saved_name

    with open(save_path, "wb") as f:
        f.write(uploaded.getbuffer())

    st.success(f"Saved to: {save_path}")
    selected_path = save_path

    try:
        df = pd.read_csv(save_path)
    except Exception as e:
        st.error(f"Failed to read uploaded CSV: {e}")
        df = None

# -----------------------------
# Preview + Import
# -----------------------------
if df is not None:
    st.write("Preview (预览):")
    st.dataframe(df.head(30), use_container_width=True)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()

    # Ensure optional cols exist
    for c in OPTIONAL_COLS:
        if c not in df.columns:
            df[c] = ""

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Import into Library (导入句型库)", type="primary"):
            conn = get_conn()
            cur = conn.cursor()

            inserted = 0
            for _, row in df.iterrows():
                pid = str(uuid.uuid4())
                scene = str(row.get("scene", "")).strip()
                en = str(row.get("en", "")).strip()
                zh = str(row.get("zh", "")).strip()
                tags = str(row.get("tags", "")).strip()
                level = str(row.get("level", "")).strip()

                if not en:
                    continue

                # ✅ MySQL: use INSERT IGNORE to avoid duplicates (depends on your unique index)
                cur.execute(
                    """
                    INSERT IGNORE INTO phrases(id, scene, en, zh, tags, level)
                    VALUES(%s, %s, %s, %s, %s, %s)
                    """,
                    (pid, scene, en, zh, tags, level),
                )
                if cur.rowcount > 0:
                    inserted += 1

            conn.commit()
            conn.close()

            st.success(f"Imported {inserted} new phrases. (重复的会自动跳过)")

    with col2:
        if selected_path and st.button("Delete this saved file (删除本地缓存文件)"):
            try:
                os.remove(selected_path)
                st.warning("Deleted. Refresh the page to update the dropdown.")
            except Exception as e:
                st.error(f"Delete failed: {e}")

else:
    st.info("Choose a saved CSV above, or upload a new one. (先选一个历史文件或上传新文件)")
