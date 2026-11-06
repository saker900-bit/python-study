"""밈 탐정 서버: 도감 내려주기 + Claude로 밈 찾기.

API 키는 서버에만 둔다 (앱 안에 넣지 말 것).
  export ANTHROPIC_API_KEY=sk-ant-...
  uvicorn main:app --port 8000
"""
import json
import time
from collections import defaultdict, deque
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

CATALOG_PATH = Path(__file__).resolve().parent.parent / "catalog.json"
MODEL = "claude-opus-5-5"
DAILY_LIMIT = 60  # IP당 하루 검색 횟수

app = FastAPI(title="밈 탐정")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
client = anthropic.Anthropic()

_catalog = {"mtime": 0.0, "data": None}


def catalog() -> dict:
    """catalog.json 이 바뀌면 다시 읽는다 (매일 업데이트 반영)."""
    mtime = CATALOG_PATH.stat().st_mtime
    if mtime != _catalog["mtime"]:
        _catalog["data"] = json.loads(CATALOG_PATH.read_text())
        _catalog["mtime"] = mtime
    return _catalog["data"]


_hits: dict[str, deque] = defaultdict(deque)


def check_limit(ip: str) -> None:
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 86400:
        q.popleft()
    if len(q) >= DAILY_LIMIT:
        raise HTTPException(429, "오늘 검색 횟수를 다 썼어요. 내일 다시 해 주세요.")
    q.append(now)


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    rejected: list[str] = []
    wrong: list[str] = Field(default_factory=list, max_length=30)


SYSTEM = (
    "너는 한국 인터넷 밈 전문가야. 사용자가 흐릿하게 기억하는 밈 설명을 듣고, 주어진 밈 도감에서 그 밈일 가능성이 있는 항목을 고른다. "
    "관련 있는 항목만 가능성 높은 순으로 최대 5개 id를 고르고, 억지로 채우지 않는다. "
    "도감에 없더라도 확실히 아는 실제 밈이면 guess에 적고, 모르면 guess는 null로 둔다. 지어내지 않는다. "
    "사용자가 이미 아니라고 한 게 있으면 그것과 비슷하지만 다른 걸 찾는다. "
    "alt_queries에는 GIF 사이트에서 그 밈 짤이 나올 만한 짧은 검색어 4~6개를 한국어와 영어로 섞어 적는다."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "ids": {"type": "array", "items": {"type": "string"}},
        "alt_queries": {"type": "array", "items": {"type": "string"}},
        "guess": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quote": {"type": "string"},
                        "source": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["name", "quote", "source", "description"],
                    "additionalProperties": False,
                },
            ]
        },
    },
    "required": ["ids", "guess", "alt_queries"],
    "additionalProperties": False,
}


@app.get("/api/catalog")
def get_catalog():
    # 앱에는 우리가 쓴 텍스트(이름·대사·설명·검색어)만 내려준다. 짤은 앱이 KLIPY에서 직접 받음.
    data = catalog()
    return {**data, "memes": [{k: v for k, v in m.items() if k != "media"} for m in data["memes"]]}


@app.post("/api/search")
def search(body: SearchIn, request: Request):
    check_limit(request.client.host if request.client else "unknown")
    memes = catalog()["memes"]
    rejected = set(body.rejected)
    lines = "\n".join(
        f"{m['id']} | {m['name']} | {m['quote']} | {m['source']} | {m['desc']}" for m in memes if m["id"] not in rejected
    )
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            # 도감은 매번 같으니 캐시해서 비용 절약
            system=[
                {"type": "text", "text": SYSTEM},
                {"type": "text", "text": f"밈 도감 (id | 이름 | 대사 | 출처 | 설명):\n{lines}", "cache_control": {"type": "ephemeral"}},
            ],
            messages=[{"role": "user", "content": f"사용자 설명: {body.query}" + (
                f"\n이미 아니라고 한 것: {', '.join(body.wrong[:15])}" if body.wrong else "")}],
        )
    except anthropic.RateLimitError:
        raise HTTPException(503, "잠시 후 다시 해 주세요.")
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"AI 오류 ({e.status_code})")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "AI 서버에 연결하지 못했어요.")

    if resp.stop_reason == "refusal":
        return {"ids": [], "guess": None, "alt_queries": []}
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
    known = {m["id"] for m in memes}
    data["ids"] = [i for i in data.get("ids", []) if i in known and i not in rejected][:6]
    data["alt_queries"] = [q for q in data.get("alt_queries", []) if isinstance(q, str) and q.strip()][:6]
    return data
