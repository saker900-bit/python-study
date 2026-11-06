"""SQLite 저장소 (MVP 용. 사용자가 많아지면 Postgres 로 교체)."""
from __future__ import annotations

import json
import sqlite3
import threading
import time

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (uid TEXT PRIMARY KEY, ts REAL);
CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY, line TEXT, station TEXT, cause TEXT, status TEXT,
  score INTEGER, notified INTEGER DEFAULT 0, resolved_notified INTEGER DEFAULT 0,
  first_seen REAL, last_seen REAL, resolved_at REAL, summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_inc_status ON incidents(status, last_seen);
CREATE TABLE IF NOT EXISTS incident_sources (
  incident_id TEXT, kind TEXT, url TEXT, title TEXT, PRIMARY KEY (incident_id, url)
);
CREATE TABLE IF NOT EXISTS devices (
  expo_token TEXT PRIMARY KEY, app_user_id TEXT, platform TEXT, lines TEXT,
  notify_resolved INTEGER, enabled INTEGER, updated_at REAL
);
CREATE TABLE IF NOT EXISTS subscribers (app_user_id TEXT PRIMARY KEY, expires_at REAL, updated_at REAL);
"""


class Store:
    def __init__(self, path: str | None = None):
        self.db = sqlite3.connect(path or config.DB_PATH, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.db.executescript(SCHEMA)

    def x(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur.fetchall()

    # --- 중복 제거
    def mark_seen(self, uid: str) -> bool:
        """처음 보는 글이면 True"""
        with self.lock:
            cur = self.db.execute("INSERT OR IGNORE INTO seen VALUES (?, ?)", (uid, time.time()))
            self.db.commit()
            return cur.rowcount == 1

    def prune(self, days: int = 3) -> None:
        cutoff = time.time() - days * 86400
        self.x("DELETE FROM seen WHERE ts < ?", (cutoff,))

    # --- 기기 / 구독자
    def upsert_device(self, token: str, uid: str, platform: str, lines: list[str], notify_resolved: bool, enabled: bool):
        self.x(
            "INSERT INTO devices VALUES (?,?,?,?,?,?,?) ON CONFLICT(expo_token) DO UPDATE SET "
            "app_user_id=excluded.app_user_id, platform=excluded.platform, lines=excluded.lines, "
            "notify_resolved=excluded.notify_resolved, enabled=excluded.enabled, updated_at=excluded.updated_at",
            (token, uid, platform, json.dumps(lines), int(notify_resolved), int(enabled), time.time()),
        )

    def delete_device(self, token: str):
        self.x("DELETE FROM devices WHERE expo_token=?", (token,))

    def set_subscriber(self, uid: str, expires_at: float | None):
        self.x(
            "INSERT INTO subscribers VALUES (?,?,?) ON CONFLICT(app_user_id) DO UPDATE SET "
            "expires_at=excluded.expires_at, updated_at=excluded.updated_at",
            (uid, expires_at or 0, time.time()),
        )

    def recipients(self, line: str | None, resolved: bool) -> list[str]:
        now = time.time()
        rows = self.x(
            "SELECT d.expo_token, d.app_user_id, d.lines, d.notify_resolved, s.expires_at FROM devices d "
            "LEFT JOIN subscribers s ON s.app_user_id = d.app_user_id WHERE d.enabled = 1"
        )
        out = []
        for r in rows:
            active = (r["expires_at"] or 0) > now or (config.DEV_MODE and r["app_user_id"].startswith("mock_"))
            if not active or (resolved and not r["notify_resolved"]):
                continue
            wanted = json.loads(r["lines"] or "[]")
            if wanted and line and line not in wanted:
                continue
            out.append(r["expo_token"])
        return out
