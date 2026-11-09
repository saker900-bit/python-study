"""SQLite 저장소. 표준 라이브러리 sqlite3만 사용한다."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("YEONRAK_DB", "yeonrak.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    invite_code TEXT NOT NULL UNIQUE,
    status TEXT,                -- "회식 중", "운동 중" 같은 내 상태 (선택)
    status_at TEXT
);
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY,
    user_a INTEGER NOT NULL REFERENCES users(id),
    user_b INTEGER NOT NULL REFERENCES users(id),
    a_calls_b TEXT NOT NULL,    -- A가 B를 부르는 이름 (예: 엄마)
    b_calls_a TEXT NOT NULL,    -- B가 A를 부르는 이름 (예: 아들)
    relation TEXT NOT NULL,     -- dating / spouse / parent / friend
    threshold_hours REAL NOT NULL,
    created_at TEXT NOT NULL,
    last_contact_at TEXT NOT NULL,
    last_reminded_at TEXT
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    link_id INTEGER NOT NULL REFERENCES links(id),
    by_user INTEGER NOT NULL REFERENCES users(id),
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nudges (
    id INTEGER PRIMARY KEY,
    link_id INTEGER NOT NULL REFERENCES links(id),
    from_user INTEGER NOT NULL REFERENCES users(id),
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,         -- reminder / nudge / contact
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    link_id INTEGER,
    created_at TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0
);
"""


def init_db(path: str | None = None) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect(path: str | None = None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
