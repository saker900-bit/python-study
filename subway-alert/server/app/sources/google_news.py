"""구글 뉴스 RSS — 무료, 키 불필요. when:1h 로 최근 1시간 기사만."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx

from .base import Post, Source

QUERIES = [
    "지하철 지연", "전철 지연", "호선 운행 중단", "호선 열차 고장",
    "지하철 운행 재개", "호선 정상 운행", "스크린도어 고장 지하철", "지하철 환자 지연",
]


class GoogleNews(Source):
    name = "google_news"

    async def fetch(self, client: httpx.AsyncClient) -> list[Post]:
        posts: list[Post] = []
        for q in QUERIES:
            url = f"https://news.google.com/rss/search?q={quote(q + ' when:1h')}&hl=ko&gl=KR&ceid=KR:ko"
            r = await client.get(url)
            r.raise_for_status()
            for item in ET.fromstring(r.content).iter("item"):
                link = item.findtext("link") or ""
                title = item.findtext("title") or ""
                desc = item.findtext("description") or ""
                pub = item.findtext("pubDate")
                if not (link and pub):
                    continue
                posts.append(Post("news", link, f"{title} {desc}", link, parsedate_to_datetime(pub)))
        return posts
