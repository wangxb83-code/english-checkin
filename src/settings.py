from __future__ import annotations
from .db import get_conn

DEFAULTS = {
    "daily_n": "15",  # default, range 10-30
    "seed": "42",
}

def get_setting(key: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    # ✅ MySQL placeholder uses %s
    cur.execute("SELECT value FROM settings WHERE `key`=%s", (key,))
    row = cur.fetchone()
    conn.close()
    if row and row.get("value") is not None:
        return str(row["value"])
    return DEFAULTS.get(key, "")

def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    # ✅ MySQL UPSERT syntax
    cur.execute("""
      INSERT INTO settings(`key`, `value`)
      VALUES(%s, %s)
      ON DUPLICATE KEY UPDATE `value`=VALUES(`value`)
    """, (key, value))
    conn.commit()
    conn.close()
