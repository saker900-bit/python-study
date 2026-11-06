"""HTTP API: 앱 피드 조회, 기기 등록, RevenueCat 구독 웹훅."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import config
from .engine import Engine
from .store import Store
from .worker import run_forever

logging.basicConfig(level=logging.INFO)
store = Store()
engine = Engine(store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(run_forever(store)) if config.RUN_WORKER else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="지하철 지연알림", lifespan=lifespan)


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/v1/incidents")
def incidents(hours: int = 24):
    return [{
        "id": i["id"], "line": i["line"], "station": i["station"], "cause": i["cause"],
        "status": i["status"], "summary": i["summary"], "first_seen": _iso(i["first_seen"]),
        "resolved_at": _iso(i["resolved_at"]), "sources": i["sources"],
    } for i in engine.recent(min(hours, 72))]


class DeviceIn(BaseModel):
    expo_token: str
    app_user_id: str
    platform: str
    lines: list[str] = []
    notify_resolved: bool = True
    enabled: bool = True


@app.post("/v1/devices")
def register(d: DeviceIn):
    if not d.expo_token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
        raise HTTPException(400, "invalid token")
    store.upsert_device(d.expo_token, d.app_user_id, d.platform, d.lines, d.notify_resolved, d.enabled)
    return {"ok": True}


@app.post("/v1/webhooks/revenuecat")
def revenuecat(body: dict, authorization: str = Header(default="")):
    """RevenueCat 대시보드 > Integrations > Webhooks 에 이 URL 과 Authorization 값을 등록."""
    if not config.REVENUECAT_WEBHOOK_AUTH or authorization != config.REVENUECAT_WEBHOOK_AUTH:
        raise HTTPException(401)
    ev = body.get("event") or {}
    ents = ev.get("entitlement_ids") or ([ev["entitlement_id"]] if ev.get("entitlement_id") else [])
    if ents and config.ENTITLEMENT_ID not in ents:
        return {"ok": True}
    expires_ms = ev.get("expiration_at_ms")
    expires = expires_ms / 1000 if expires_ms else None
    if ev.get("type") == "EXPIRATION":
        expires = 0
    # CANCELLATION 은 자동갱신만 꺼진 것 → 만료일까지는 계속 이용 가능하므로 expiration 그대로 저장
    ids = {ev.get("app_user_id"), ev.get("original_app_user_id"), *(ev.get("aliases") or [])}
    for uid in filter(None, ids):
        store.set_subscriber(uid, expires)
    return {"ok": True}
