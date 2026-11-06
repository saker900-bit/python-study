from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx


@dataclass
class Post:
    source: str  # "news" | "x" | "instagram" | "official"
    uid: str  # 중복 제거용 고유값 (보통 URL)
    text: str
    url: str
    published: datetime  # timezone-aware

    @property
    def weight(self) -> int:
        """신뢰도 점수: 공식 3, 뉴스 2, SNS 1"""
        return {"official": 3, "news": 2}.get(self.source, 1)


class Source:
    name = "base"

    def available(self) -> bool:
        return True

    async def fetch(self, client: httpx.AsyncClient) -> list[Post]:
        raise NotImplementedError
