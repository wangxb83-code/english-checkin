from __future__ import annotations
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST") or os.getenv("MYSQLHOST") or "localhost"
DB_PORT = int(os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or 3306)
DB_USER = os.getenv("DB_USER") or os.getenv("MYSQLUSER") or "root"
DB_PASSWORD = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD") or ""
DB_NAME = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE") or ""


# -----------------------
# Connection
# -----------------------
def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


# -----------------------
# Init tables (IDEMPOTENT)
# -----------------------
def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    # phrases
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phrases (
      id VARCHAR(36) PRIMARY KEY,
      scene VARCHAR(100),
      en TEXT NOT NULL,
      zh TEXT,
      tags VARCHAR(255),
      level VARCHAR(20),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ---- safe unique index ----
    cur.execute("""
    SELECT COUNT(1) AS c
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'phrases'
      AND INDEX_NAME = 'idx_phrases_unique'
    """)
    exists = cur.fetchone()["c"] > 0

    if not exists:
        cur.execute("""
        CREATE UNIQUE INDEX idx_phrases_unique
        ON phrases(scene(100), en(255));
        """)

    # progress
    cur.execute("""
    CREATE TABLE IF NOT EXISTS progress (
      phrase_id VARCHAR(36) PRIMARY KEY,
      mastery INT DEFAULT 0,
      last_seen TIMESTAMP NULL,
      seen_count INT DEFAULT 0,
      FOREIGN KEY (phrase_id) REFERENCES phrases(id)
    );
    """)

    # decks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS decks (
      deck_date DATE NOT NULL,
      phrase_id VARCHAR(36) NOT NULL,
      status VARCHAR(20) DEFAULT 'pending',
      result VARCHAR(20),
      PRIMARY KEY (deck_date, phrase_id),
      FOREIGN KEY (phrase_id) REFERENCES phrases(id)
    );
    """)

    # checkins
    cur.execute("""
    CREATE TABLE IF NOT EXISTS checkins (
      check_date DATE PRIMARY KEY,
      target_n INT NOT NULL,
      done_n INT NOT NULL,
      is_completed TINYINT NOT NULL,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
    );
    """)

    # settings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
      `key` VARCHAR(50) PRIMARY KEY,
      `value` VARCHAR(255)
    );
    """)

    conn.commit()
    conn.close()
