"""수집 루프: 모든 소스를 주기적으로 긁어서 사건 처리 → 푸시."""
from __future__ import annotations

import asyncio
import logging

import httpx

from . import config
from .engine import Engine
from .push import send
from .sources import enabled_sources
from .store import Store

log = logging.getLogger(__name__)


async def tick(engine: Engine, sources, client: httpx.AsyncClient) -> None:
    results = await asyncio.gather(*(s.fetch(client) for s in sources), return_exceptions=True)
    posts = []
    for s, r in zip(sources, results):
        if isinstance(r, Exception):
            log.warning("source %s failed: %r", s.name, r)
        else:
            posts += r
    notices = engine.process(posts)
    if notices:
        await send(engine.s, notices, client)


async def run_forever(store: Store) -> None:
    engine = Engine(store)
    sources = enabled_sources()
    log.info("sources: %s", [s.name for s in sources])
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "subway-alert/1.0"}) as client:
        n = 0
        while True:
            try:
                await tick(engine, sources, client)
            except Exception:
                log.exception("tick failed")
            n += 1
            if n % 100 == 0:
                store.prune()
            await asyncio.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever(Store()))
