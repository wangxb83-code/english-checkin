from __future__ import annotations
import hashlib
import random
from datetime import date
from .db import get_conn
from .settings import get_setting


def _seed_for_day(day: str) -> int:
    seed_base = get_setting("seed") or "42"
    s = f"{day}:{seed_base}".encode("utf-8")
    return int(hashlib.md5(s).hexdigest()[:8], 16)


def ensure_today_deck(today: str | None = None) -> None:
    if today is None:
        today = date.today().isoformat()

    conn = get_conn()
    cur = conn.cursor()

    # ✅ MySQL placeholder uses %s (not ?)
    cur.execute("SELECT COUNT(1) AS c FROM decks WHERE deck_date=%s", (today,))
    if cur.fetchone()["c"] > 0:
        conn.close()
        return

    daily_n = int(get_setting("daily_n") or "15")
    daily_n = max(10, min(30, daily_n))

    cur.execute("""
      SELECT p.id,
             COALESCE(pr.mastery, 0) AS mastery
      FROM phrases p
      LEFT JOIN progress pr ON pr.phrase_id = p.id
    """)
    rows = cur.fetchall()
    if not rows:
        conn.close()
        return

    unseen = [r["id"] for r in rows if r["mastery"] == 0]
    learning = [r["id"] for r in rows if r["mastery"] == 1]
    known = [r["id"] for r in rows if r["mastery"] == 2]

    rnd = random.Random(_seed_for_day(today))
    rnd.shuffle(unseen)
    rnd.shuffle(learning)
    rnd.shuffle(known)

    picked: list[str] = []
    for pool in (unseen, learning, known):
        for pid in pool:
            if len(picked) >= daily_n:
                break
            picked.append(pid)
        if len(picked) >= daily_n:
            break

    # ✅ executemany with %s placeholders
    cur.executemany(
        "INSERT INTO decks(deck_date, phrase_id) VALUES(%s, %s)",
        [(today, pid) for pid in picked],
    )

    conn.commit()
    conn.close()
