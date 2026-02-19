import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.db import get_conn

st.title("Stats")

conn = get_conn()
cur = conn.cursor()

end = date.today()
start = end - timedelta(days=29)

# ✅ MySQL placeholders: %s
cur.execute(
    """
    SELECT check_date, target_n, done_n, is_completed
    FROM checkins
    WHERE check_date BETWEEN %s AND %s
    ORDER BY check_date DESC
    """,
    (start.isoformat(), end.isoformat()),
)
rows = cur.fetchall()
conn.close()

# Build full 30-day frame
data = {str(r["check_date"]): r for r in rows}
days = [(end - timedelta(days=i)).isoformat() for i in range(30)]

records = []
for d in days:
    if d in data:
        r = data[d]
        records.append([
            d,
            int(r["target_n"]),
            int(r["done_n"]),
            "✅" if int(r["is_completed"]) == 1 else "❌",
        ])
    else:
        records.append([d, 0, 0, "❌"])

df = pd.DataFrame(records, columns=["date", "target_n", "done_n", "completed"])
st.dataframe(df, use_container_width=True)

# streak: from today backwards
streak = 0
for d in days:
    if d in data and int(data[d]["is_completed"]) == 1:
        streak += 1
    else:
        break

st.metric("Current streak (连续打卡)", streak)
