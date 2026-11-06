"""인스타그램 해시태그 검색 — Instagram Graph API.
비즈니스/크리에이터 계정 + Meta 앱 심사 필요, 7일에 해시태그 30개 제한.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from .. import config
from .base import Post, Source

HASHTAGS = ["지하철지연", "지하철고장", "출근길지옥철"]
GRAPH = "https://graph.facebook.com/v21.0"


class Instagram(Source):
    name = "instagram"

    def __init__(self) -> None:
        self.tag_ids: dict[str, str] = {}

    def available(self) -> bool:
        return bool(config.IG_USER_ID and config.IG_ACCESS_TOKEN)

    async def fetch(self, client: httpx.AsyncClient) -> list[Post]:
        auth = {"user_id": config.IG_USER_ID, "access_token": config.IG_ACCESS_TOKEN}
        posts: list[Post] = []
        for tag in HASHTAGS:
            if tag not in self.tag_ids:
                r = await client.get(f"{GRAPH}/ig_hashtag_search", params={**auth, "q": tag})
                r.raise_for_status()
                data = r.json().get("data") or []
                if not data:
                    continue
                self.tag_ids[tag] = data[0]["id"]
            r = await client.get(f"{GRAPH}/{self.tag_ids[tag]}/recent_media",
                                 params={**auth, "fields": "id,caption,permalink,timestamp", "limit": 50})
            r.raise_for_status()
            for m in r.json().get("data", []):
                if not m.get("caption"):
                    continue
                ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
                posts.append(Post("instagram", m["permalink"], m["caption"], m["permalink"], ts))
        return posts
