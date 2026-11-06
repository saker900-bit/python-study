"""X(트위터) 최근 검색 API — 유료 플랜(Basic 이상) 필요. https://developer.x.com"""
from __future__ import annotations

from datetime import datetime

import httpx

from .. import config
from .base import Post, Source

QUERY = ("(지하철 OR 전철 OR 호선 OR 신분당선 OR 수인분당선 OR 경의중앙선 OR 공항철도) "
         "(지연 OR 운행중단 OR \"운행 중단\" OR 멈춤 OR 고장 OR \"운행 재개\" OR 정상운행) "
         "-is:retweet lang:ko")
# 공식 계정은 신뢰도 높게 취급 (실제 핸들은 확인 후 채워 넣을 것)
OFFICIAL_HANDLES: set[str] = set()


class XRecentSearch(Source):
    name = "x"

    def __init__(self) -> None:
        self.since_id: str | None = None

    def available(self) -> bool:
        return bool(config.X_BEARER_TOKEN)

    async def fetch(self, client: httpx.AsyncClient) -> list[Post]:
        params = {
            "query": QUERY,
            "max_results": 100,
            "tweet.fields": "created_at,author_id",
            "expansions": "author_id",
            "user.fields": "username",
        }
        if self.since_id:
            params["since_id"] = self.since_id
        r = await client.get("https://api.x.com/2/tweets/search/recent", params=params,
                             headers={"Authorization": f"Bearer {config.X_BEARER_TOKEN}"})
        r.raise_for_status()
        body = r.json()
        users = {u["id"]: u["username"] for u in body.get("includes", {}).get("users", [])}
        posts = []
        for t in body.get("data", []):
            handle = users.get(t.get("author_id"), "i")
            url = f"https://x.com/{handle}/status/{t['id']}"
            kind = "official" if handle.lower() in OFFICIAL_HANDLES else "x"
            posts.append(Post(kind, url, t["text"], url,
                              datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))))
        if body.get("meta", {}).get("newest_id"):
            self.since_id = body["meta"]["newest_id"]
        return posts
