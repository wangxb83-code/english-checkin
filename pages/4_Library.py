import streamlit as st
import pandas as pd
from src.db import get_conn

st.title("Library")

conn = get_conn()
cur = conn.cursor()

scene = st.text_input("Filter by scene (场景)", "")
keyword = st.text_input("Search keyword (关键词)", "")

q = "SELECT scene, en, zh, tags, level FROM phrases WHERE 1=1"
params = []

if scene.strip():
    q += " AND scene LIKE %s"
    params.append(f"%{scene.strip()}%")

if keyword.strip():
    q += " AND (en LIKE %s OR zh LIKE %s OR tags LIKE %s)"
    kw = f"%{keyword.strip()}%"
    params.extend([kw, kw, kw])

q += " ORDER BY created_at DESC LIMIT 500"

# ✅ MySQL: placeholders are %s, params最好转 tuple
cur.execute(q, tuple(params))
rows = cur.fetchall()
conn.close()

df = pd.DataFrame(rows)  # PyMySQL DictCursor already returns dicts
st.dataframe(df, use_container_width=True)
