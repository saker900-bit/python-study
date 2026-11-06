from .base import Post, Source
from .google_news import GoogleNews
from .instagram import Instagram
from .naver import NaverNews
from .x_twitter import XRecentSearch


def enabled_sources() -> list[Source]:
    """키가 설정된 소스만 켠다. 구글 뉴스 RSS 는 키 없이 항상 동작."""
    srcs: list[Source] = [GoogleNews()]
    for cls in (NaverNews, XRecentSearch, Instagram):
        s = cls()
        if s.available():
            srcs.append(s)
    return srcs


__all__ = ["Post", "Source", "enabled_sources"]
