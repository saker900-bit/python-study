"""네이버 뉴스 검색 API — 무료(일 25,000회). https://developers.naver.com 에서 키 발급."""
from __future__ import annotations

from email.utils import parsedate_to_datetime

import httpx

from .. import config
from .base import Post, Source

QUERIES = ["지하철 지연", "전철 운행 중단", "열차 고장 지연", "지하철 운행 재개"]


class NaverNews(Source):
    name = "naver_news"

    def available(self) -> bool:
        return bool(config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET)

    async def fetch(self, client: httpx.AsyncClient) -> list[Post]:
        headers = {
            "X-Naver-Client-Id": config.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET,
        }
        posts: list[Post] = []
        for q in QUERIES:
            r = await client.get(
                "https://openapi.naver.com/v1/search/news.json",
                params={"query": q, "display": 30, "sort": "date"},
                headers=headers,
            )
            r.raise_for_status()
            for it in r.json().get("items", []):
                url = it.get("originallink") or it["link"]
                posts.append(Post("news", url, f"{it['title']} {it['description']}", url,
                                  parsedate_to_datetime(it["pubDate"])))
        return posts
