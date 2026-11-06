"""Expo 푸시 서비스로 iOS/Android 알림 발송."""
from __future__ import annotations

import logging

import httpx

from . import config
from .engine import Notice
from .lines import LINE_NAMES
from .store import Store

log = logging.getLogger(__name__)
EXPO_URL = "https://exp.host/--/api/v2/push/send"


def format_notice(n: Notice) -> tuple[str, str]:
    inc = n.incident
    where = " ".join(x for x in [LINE_NAMES.get(inc["line"] or ""), inc["station"] and f"{inc['station']}역"] if x)
    if n.kind == "delay":
        return f"🚨 {where} 지연", f"{inc['cause']}(으)로 열차 운행이 지연되고 있어요."
    return f"✅ {where} 정상 운행", f"{inc['cause']} 상황이 해소돼 운행이 재개됐어요."


async def send(store: Store, notices: list[Notice], client: httpx.AsyncClient) -> int:
    sent = 0
    for n in notices:
        title, body = format_notice(n)
        tokens = store.recipients(n.incident["line"], resolved=n.kind == "resolved")
        msgs = [{
            "to": t, "title": title, "body": body, "sound": "default", "priority": "high",
            "channelId": "delay" if n.kind == "delay" else "resolved",
            "data": {"incidentId": n.incident["id"], "kind": n.kind},
        } for t in tokens]
        headers = {"Authorization": f"Bearer {config.EXPO_ACCESS_TOKEN}"} if config.EXPO_ACCESS_TOKEN else {}
        for i in range(0, len(msgs), 100):  # Expo 는 요청당 최대 100건
            batch = msgs[i:i + 100]
            try:
                r = await client.post(EXPO_URL, json=batch, headers=headers)
                r.raise_for_status()
            except httpx.HTTPError as e:
                log.warning("push failed: %s", e)
                continue
            for msg, ticket in zip(batch, r.json().get("data", [])):
                if ticket.get("status") == "ok":
                    sent += 1
                elif ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                    store.delete_device(msg["to"])  # 앱 삭제한 기기 정리
        log.info("notice %s %s → %d devices", n.kind, title, len(tokens))
    return sent
