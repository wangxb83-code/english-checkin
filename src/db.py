from __future__ import annotations

import os
from typing import Optional

import pymysql


# -----------------------
# Env helpers
# -----------------------
def _get_env(key: str, fallback: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    return v if (v is not None and v != "") else fallback


def _is_railway() -> bool:
    # Railway usually sets RAILWAY_ENVIRONMENT, RAILWAY_PROJECT_ID etc.
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))


def _mysql_config():
    """
    Prefer Railway vars, then your custom DB_* vars.
    Do NOT default to localhost on Railway.
    """
    host = _get_env("MYSQLHOST") or _get_env("DB_HOST")
    port = _get_env("MYSQLPORT") or _get_env("DB_PORT") or "3306"
    user = _get_env("MYSQLUSER") or _get_env("DB_USER")
    password = _get_env("MYSQLPASSWORD") or _get_env("DB_PASSWORD")
    database = _get_env("MYSQLDATABASE") or _get_env("DB_NAME")

    # On Railway, host/user/database should exist. If missing -> fail fast.
    if _is_railway():
        missing = [k for k, v in {
            "MYSQLHOST/DB_HOST": host,
            "MYSQLUSER/DB_USER": user,
            "MYSQLDATABASE/DB_NAME": database,
        }.items() if not v]
        if missing:
            raise RuntimeError(
                "MySQL env vars are missing on Railway: "
                + ", ".join(missing)
                + ".\nGo to Railway -> your MySQL service -> Variables, then "
                  "make sure they are available in your web service Variables."
            )

        # Extra safety: never allow localhost on Railway
        if host in ("localhost", "127.0.0.1"):
            raise RuntimeError(
                "DB_HOST is localhost on Railway. Use MYSQLHOST provided by Railway MySQL service."
            )

    # For local dev, allow localhost only if user explicitly sets it
    if not host:
        host = "localhost"
    return host, int(port), user or "root", password or "", database or ""


# -----------------------
# Connection
# -----------------------
def get_conn():
    host, port, user, password, database = _mysql_config()
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS phrases (
          id VARCHAR(36) PRIMARY KEY,
          scene VARCHAR(100),
          en TEXT NOT NULL,
          zh TEXT,
          tags VARCHAR(255),
          level VARCHAR(20),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # safe unique index
    cur.execute(
        """
        SELECT COUNT(1) AS c
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'phrases'
          AND INDEX_NAME = 'idx_phrases_unique'
        """
    )
    row = cur.fetchone() or {}
    exists = int(row.get("c", 0)) > 0

    if not exists:
        cur.execute(
            """
            CREATE UNIQUE INDEX idx_phrases_unique
            ON phrases(scene(100), en(255));
            """
        )

    # progress
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS progress (
          phrase_id VARCHAR(36) PRIMARY KEY,
          mastery INT DEFAULT 0,
          last_seen TIMESTAMP NULL,
          seen_count INT DEFAULT 0,
          FOREIGN KEY (phrase_id) REFERENCES phrases(id)
        );
        """
    )

    # decks
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS decks (
          deck_date DATE NOT NULL,
          phrase_id VARCHAR(36) NOT NULL,
          status VARCHAR(20) DEFAULT 'pending',
          result VARCHAR(20),
          PRIMARY KEY (deck_date, phrase_id),
          FOREIGN KEY (phrase_id) REFERENCES phrases(id)
        );
        """
    )

    # checkins
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS checkins (
          check_date DATE PRIMARY KEY,
          target_n INT NOT NULL,
          done_n INT NOT NULL,
          is_completed TINYINT NOT NULL,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP
        );
        """
    )

    # settings
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
          `key` VARCHAR(50) PRIMARY KEY,
          `value` VARCHAR(255)
        );
        """
    )

    conn.commit()
    conn.close()
