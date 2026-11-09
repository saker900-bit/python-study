from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import ai, db, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(main, "CHECK_INTERVAL_SEC", 0)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with TestClient(main.app) as c:
        yield c


def signup(c, name):
    u = c.post("/api/users", json={"name": name}).json()
    return u, {"X-Token": u["token"]}


def make_pair(c):
    mom, mh = signup(c, "엄마")
    son, sh = signup(c, "철수")
    r = c.post("/api/links", headers=sh, json={
        "invite_code": mom["invite_code"], "relation": "parent",
        "i_call_them": "엄마", "they_call_me": "아들"})
    assert r.status_code == 200, r.text
    return r.json(), mh, sh


def test_link_and_views(client):
    link, mh, sh = make_pair(client)
    assert link["their_name"] == "엄마" and link["threshold_hours"] == 72
    mom_view = client.get("/api/links", headers=mh).json()[0]
    assert mom_view["their_name"] == "아들"
    # 엄마는 연결 알림을 받는다
    notes = client.get("/api/notifications", headers=mh).json()
    assert notes[0]["kind"] == "linked"
    assert client.get("/api/notifications", headers=mh).json() == []  # 한 번만 전달


def test_nudge_sends_push_and_cooldown(client):
    link, mh, sh = make_pair(client)
    client.get("/api/notifications", headers=mh)
    assert client.post(f"/api/links/{link['id']}/nudge", headers=mh).status_code == 200
    notes = client.get("/api/notifications", headers=sh).json()
    assert notes[-1]["kind"] == "nudge" and "연락 안 하냐" in notes[-1]["title"]
    assert client.post(f"/api/links/{link['id']}/nudge", headers=mh).status_code == 429


def test_reminder_after_threshold_and_contact_resets(client):
    link, mh, sh = make_pair(client)
    client.get("/api/notifications", headers=mh)
    later = main.now() + timedelta(hours=73)
    assert main.check_reminders(later) == 2          # 양쪽 다
    assert main.check_reminders(later) == 0          # 중복 없음
    n = client.get("/api/notifications", headers=sh).json()
    assert n[-1]["kind"] == "reminder" and "엄마" in n[-1]["title"]
    client.post(f"/api/links/{link['id']}/contact", headers=sh)
    assert client.get("/api/notifications", headers=mh).json()[-1]["kind"] == "contact"
    assert main.check_reminders(main.now() + timedelta(hours=1)) == 0


def test_stranger_cannot_touch_link(client):
    link, mh, sh = make_pair(client)
    _, xh = signup(client, "남")
    assert client.post(f"/api/links/{link['id']}/nudge", headers=xh).status_code == 404
    assert client.get("/api/links", headers={"X-Token": "bad"}).status_code == 401


def test_reassure_uses_status_without_api_key(client):
    link, mh, sh = make_pair(client)
    client.post("/api/me/status", headers=mh, json={"status": "동창 모임"})
    r = client.get(f"/api/links/{link['id']}/reassure", headers=sh).json()
    assert r["source"] == "rule" and "떠드느라" in r["message"]


def sit(**kw):
    base = dict(their_name="여친", relation="연인", now=datetime(2026, 11, 6, 23, 0), hours_since=3)
    base.update(kw)
    return ai.Situation(**base)


def test_rule_based_time_slots():
    fri = ai.rule_based(sit())                                                   # 금요일 밤
    assert "술" in fri or "떠드느라" in fri
    assert "자" in ai.rule_based(sit(now=datetime(2026, 11, 4, 3, 0)))           # 새벽
    assert "점심" in ai.rule_based(sit(now=datetime(2026, 11, 4, 12, 20)))      # 평일 점심
    assert "먼저" in ai.rule_based(sit(hours_since=50))                          # 오래됨


def test_ai_falls_back_on_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    def boom(_):
        raise RuntimeError("network")
    monkeypatch.setattr(ai, "_ask_claude", boom)
    assert ai.reassure(sit())["source"] == "rule"
