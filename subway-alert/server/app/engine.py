"""수집한 글 → 사건(incident) 생성/갱신/복구 → 보낼 알림 목록."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config
from .parser import Detection, parse
from .sources.base import Post
from .store import Store

GENERIC = "운행 장애"


@dataclass
class Notice:
    kind: str  # "delay" | "resolved"
    incident: dict


def _compatible(a: str | None, b: str | None) -> bool:
    return a is None or b is None or a == b


class Engine:
    def __init__(self, store: Store):
        self.s = store

    def _active(self) -> list[dict]:
        return [dict(r) for r in self.s.x("SELECT * FROM incidents WHERE status='active'")]

    def _match(self, line: str | None, d: Detection, for_resolve: bool) -> dict | None:
        for inc in self._active():
            if not _compatible(inc["line"], line) or not _compatible(inc["station"], d.station):
                continue
            # 노선과 역이 둘 다 비어서 맞는 경우는 너무 느슨하니 제외
            if not ((inc["line"] and inc["line"] == line) or (inc["station"] and inc["station"] == d.station)):
                continue
            if for_resolve or GENERIC in (inc["cause"], d.cause) or inc["cause"] == d.cause:
                return inc
        return None

    def _add_source(self, inc_id: str, post: Post, text: str) -> bool:
        before = self.s.x("SELECT 1 FROM incident_sources WHERE incident_id=? AND url=?", (inc_id, post.url))
        if before:
            return False
        self.s.x("INSERT INTO incident_sources VALUES (?,?,?,?)", (inc_id, post.source, post.url, text[:200]))
        return True

    def process(self, posts: list[Post], now: float | None = None) -> list[Notice]:
        now = now or time.time()
        notices: list[Notice] = []
        for post in sorted(posts, key=lambda p: p.published):
            if not self.s.mark_seen(post.uid):
                continue
            age_min = (datetime.fromtimestamp(now, timezone.utc) - post.published).total_seconds() / 60
            if age_min > config.MAX_POST_AGE_MIN:
                continue
            d = parse(post.text)
            if not d:
                continue
            for line in (d.lines[:3] or [None]):
                n = self._apply(post, d, line, now)
                if n:
                    notices.append(n)
        notices += self._expire(now)
        return notices

    def _apply(self, post: Post, d: Detection, line: str | None, now: float) -> Notice | None:
        if d.kind == "resolved":
            inc = self._match(line, d, for_resolve=True)
            if not inc:
                return None
            self._add_source(inc["id"], post, d.text)
            self.s.x("UPDATE incidents SET status='resolved', resolved_at=?, last_seen=?, resolved_notified=? WHERE id=?",
                     (now, now, inc["notified"], inc["id"]))
            # 처음에 지연 알림을 보낸 사건만 복구 알림
            return Notice("resolved", self.get(inc["id"])) if inc["notified"] else None

        inc = self._match(line, d, for_resolve=False)
        if inc:
            if self._add_source(inc["id"], post, d.text):
                self.s.x(
                    "UPDATE incidents SET score=score+?, last_seen=?, station=COALESCE(station, ?), line=COALESCE(line, ?), "
                    "cause=CASE WHEN cause=? THEN ? ELSE cause END WHERE id=?",
                    (post.weight, now, d.station, line, GENERIC, d.cause, inc["id"]),
                )
            inc_id = inc["id"]
        else:
            inc_id = uuid.uuid4().hex[:12]
            self.s.x(
                "INSERT INTO incidents (id,line,station,cause,status,score,first_seen,last_seen,summary) "
                "VALUES (?,?,?,?,'active',?,?,?,?)",
                (inc_id, line, d.station, d.cause, post.weight, now, now, d.text[:160]),
            )
            self._add_source(inc_id, post, d.text)
        cur = self.get(inc_id)
        if not cur["notified"] and cur["score"] >= config.PUSH_THRESHOLD:
            self.s.x("UPDATE incidents SET notified=1 WHERE id=?", (inc_id,))
            return Notice("delay", self.get(inc_id))
        return None

    def _expire(self, now: float) -> list[Notice]:
        cutoff = now - config.INCIDENT_TTL_MIN * 60
        # 오래 소식 없는 사건은 조용히 종료 (복구 확인이 안 됐으니 복구 알림은 안 보냄)
        self.s.x("UPDATE incidents SET status='resolved', resolved_at=? WHERE status='active' AND last_seen < ?",
                 (now, cutoff))
        return []

    def get(self, inc_id: str) -> dict:
        inc = dict(self.s.x("SELECT * FROM incidents WHERE id=?", (inc_id,))[0])
        inc["sources"] = [dict(r) for r in self.s.x(
            "SELECT kind, url, title FROM incident_sources WHERE incident_id=?", (inc_id,))]
        return inc

    def recent(self, hours: int = 24) -> list[dict]:
        cutoff = time.time() - hours * 3600
        rows = self.s.x("SELECT id FROM incidents WHERE last_seen > ? AND notified=1 "
                        "ORDER BY status='active' DESC, first_seen DESC LIMIT 100", (cutoff,))
        return [self.get(r["id"]) for r in rows]
