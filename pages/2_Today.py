import streamlit as st
from datetime import date

from src.db import get_conn
from src.deck import ensure_today_deck
from src.settings import get_setting

st.title("Today")

today = date.today().isoformat()
ensure_today_deck(today)

daily_n = int(get_setting("daily_n") or "15")
daily_n = max(10, min(30, daily_n))

conn = get_conn()
cur = conn.cursor()

# ✅ MySQL placeholder: %s
cur.execute("""
  SELECT d.phrase_id, d.status, d.result, p.scene, p.en, p.zh
  FROM decks d
  JOIN phrases p ON p.id = d.phrase_id
  WHERE d.deck_date=%s
  ORDER BY d.status ASC
""", (today,))
cards = cur.fetchall()

if not cards:
    st.warning("No phrases in library yet. Go to Upload page first.")
    conn.close()
    st.stop()

done_n = sum(1 for c in cards if c["status"] == "done")
st.progress(min(1.0, done_n / max(1, len(cards))))
st.write(f"Progress: **{done_n}/{len(cards)}** (Target setting: {daily_n}, actual deck: {len(cards)})")

idx = st.session_state.get("card_idx", 0)
idx = min(idx, len(cards) - 1)
card = cards[idx]

st.subheader(f"Card {idx+1}/{len(cards)} — Scene: {card.get('scene') or 'General'}")
st.markdown(f"### {card['en']}")
with st.expander("Show Chinese note (中文注释)"):
    st.write(card.get("zh") or "—")

col1, col2, col3, col4 = st.columns(4)

def mark_done(result: str | None):
    # 1) update deck row
    cur.execute("""
      UPDATE decks SET status=%s, result=%s
      WHERE deck_date=%s AND phrase_id=%s
    """, ("done", result, today, card["phrase_id"]))

    # 2) read progress
    cur.execute("SELECT mastery, seen_count FROM progress WHERE phrase_id=%s", (card["phrase_id"],))
    pr = cur.fetchone()
    mastery = int(pr["mastery"]) if pr else 0
    seen_count = int(pr["seen_count"]) if pr else 0

    seen_count += 1
    if result == "known":
        mastery = 2
    elif result == "unknown":
        mastery = max(1, mastery)

    # 3) upsert progress (MySQL)
    cur.execute("""
      INSERT INTO progress(phrase_id, mastery, last_seen, seen_count)
      VALUES(%s, %s, NOW(), %s)
      ON DUPLICATE KEY UPDATE
        mastery=VALUES(mastery),
        last_seen=VALUES(last_seen),
        seen_count=VALUES(seen_count)
    """, (card["phrase_id"], mastery, seen_count))

    conn.commit()
    st.session_state["card_idx"] = min(len(cards) - 1, idx + 1)

with col1:
    if st.button("✅ (Known)"):
        mark_done("known")
        st.rerun()

with col2:
    if st.button("🟨 (Need review)"):
        mark_done("unknown")
        st.rerun()

with col3:
    if st.button("⏭️ (Skip)"):
        cur.execute("""
          UPDATE decks SET status=%s
          WHERE deck_date=%s AND phrase_id=%s
        """, ("skipped", today, card["phrase_id"]))
        conn.commit()
        st.session_state["card_idx"] = min(len(cards) - 1, idx + 1)
        st.rerun()

with col4:
    if st.button("🔄 (Back to first)"):
        st.session_state["card_idx"] = 0
        st.rerun()

# ---- update checkin summary ----
cur.execute("SELECT COUNT(1) AS total FROM decks WHERE deck_date=%s", (today,))
total = int(cur.fetchone()["total"])
cur.execute("SELECT COUNT(1) AS done FROM decks WHERE deck_date=%s AND status=%s", (today, "done"))
done = int(cur.fetchone()["done"])

# MVP: 完成当日 deck 即成功（如想改成 done >= daily_n，我也能给你一行改法）
is_completed = 1 if done >= total else 0

cur.execute("""
  INSERT INTO checkins(check_date, target_n, done_n, is_completed)
  VALUES(%s, %s, %s, %s)
  ON DUPLICATE KEY UPDATE
    target_n=VALUES(target_n),
    done_n=VALUES(done_n),
    is_completed=VALUES(is_completed),
    updated_at=NOW()
""", (today, daily_n, done, is_completed))

conn.commit()

if is_completed:
    st.success("🎉 打卡成功！Check-in completed.")
else:
    st.info("Not completed yet. Keep going!")

conn.close()
