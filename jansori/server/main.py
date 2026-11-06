"""잔소리 탐지기 서버.

앱이 평소 사진과 오늘 사진을 보내면 Claude가 비교해서
달라진 곳(위치 포함)과 잔소리 대사를 JSON으로 돌려준다.

API 키는 앱에 넣으면 털리기 때문에 반드시 이 서버에만 둔다.

목소리(선택): ElevenLabs 키가 있으면 잔소리를 자연스러운 음성으로 만들고,
목소리 샘플로 그 사람 목소리를 복제할 수 있다.

실행:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...
    export ELEVENLABS_API_KEY=...            # 선택
    export ELEVENLABS_VOICE_AJUMMA=<voice_id> # 선택: 캐릭터별 기본 목소리
    export ELEVENLABS_VOICE_HALMEONI=...
    export ELEVENLABS_VOICE_AJEOSSI=...
    export ELEVENLABS_VOICE_KID=...
    uvicorn main:app --reload --port 8000
"""

import base64
import json
import os

import httpx

import anthropic
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

MODEL = "claude-opus-5-5"

# (이름, 잔소리 예시, 마무리 잔소리 예시)
PERSONAS = {
    "ajumma": ("아줌마", ["이거 뭐야!", "이거 치워!", "내가 몇 번을 말했니!"],
               ["으휴~ 이래서 내가 집을 비울 수가 없어~", "하여간 이 집구석은 내가 없으면 돌아가질 않아~", "어지르는 사람 따로 있고 치우는 사람 따로 있니?"]),
    "halmeoni": ("할머니", ["아이고 이게 다 뭐꼬!", "이거 얼른 치아라!", "니 이래 살면 못 쓴다!"],
                 ["아이고~ 할미가 없으면 이 집이 우째 돌아가노~", "어지르는 사람 따로 있고 치우는 사람 따로 있나!"]),
    "ajeossi": ("아저씨", ["어허! 이게 뭐야!", "당장 치워라!", "정리 좀 하고 살자!"],
                ["어휴, 내가 집을 비울 수가 없다니까!", "어지르는 사람 따로 있고 치우는 사람 따로 있냐?"]),
    "kid": ("어린아이", ["이거 엄마한테 이를 거야!", "으악 이게 뭐야~", "치워 치워!"],
            ["어지른 사람이 치우는 거야! 유치원에서 배웠어!", "으휴~ 내가 없으면 이 집 어떡해~"]),
}

# 눈썰미 (web/index.html 의 MODES 와 같은 내용)
MODES = {
    "obsess": "아주 작은 차이까지 전부 찾아라. 물건이 몇 cm 옮겨진 것, 쿠션·이불 주름이나 각도, 리모컨·슬리퍼 방향, 먼지, 얼룩, 머리카락, 살짝 열린 서랍이나 문, 비뚤어진 액자까지. 사진 각도 차이만 빼고 사소한 것도 빠짐없이. 최대 12개.",
    "mom": "보통 한국 엄마·아내 눈썰미로 찾아라. 잔소리할 만한 것 위주로, 아주 사소한 차이(몇 cm 이동, 미세한 각도)는 무시. 최대 6개.",
    "dad": "눈에 확 띄는 변화 위주로 찾아라. 최대 6개.",
}

# 응답 모양을 강제하는 JSON 스키마 (web/index.html 의 cleanResult 와 맞춤)
RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "closing": {"type": "string"},
        "score": {"type": "integer"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "line": {"type": "string"},
                    "kind": {"type": "string", "enum": ["new", "moved", "missing", "messy"]},
                    "size": {"type": "string", "enum": ["big", "small"]},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "w": {"type": "number"},
                    "h": {"type": "number"},
                },
                "required": ["label", "line", "kind", "size", "x", "y", "w", "h"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "closing", "score", "items"],
    "additionalProperties": False,
}


def build_prompt(voice: str, spice: int, mode: str = "mom") -> str:
    """web/index.html 의 buildPrompt 와 같은 내용."""
    name, examples, closers = PERSONAS.get(voice, PERSONAS["ajumma"])
    ask = MODES.get(mode, MODES["mom"])
    ex = ", ".join(f'"{s}"' for s in examples)
    cl = ", ".join(f'"{s}"' for s in closers)
    return f"""너는 "잔소리 탐지기" 앱의 눈이다. 사진 두 장이 주어진다.
첫 번째 사진: 이 방의 평소(깨끗한) 모습. 두 번째 사진: 오늘 모습.
두 사진을 비교해서 평소와 달라진 것, 특히 엄마나 아내가 잔소리할 만한 것을 찾아라.
예: 새로 생긴 물건, 바닥/소파/식탁에 널린 것, 쌓인 빨래나 설거지, 쓰레기, 열린 문이나 서랍, 사라지거나 자리가 바뀐 물건.
조명 차이, 사진 각도 차이, 그림자 차이는 무시해라.
{ask}
중요도 높은 순서로.

각 항목마다:
- label: 무엇인지 짧게 (예: "소파 위 빨래")
- line: {name} 말투로 그 물건을 손가락으로 찝으며 하는 잔소리 한두 마디. 맵기 {spice}단계(1 순한맛, 2 보통, 3 매운맛). 욕설·비하 금지, 웃기게.
  {name} 말투 예시: {ex}
- kind: "new"(새로 생김) | "moved"(자리 바뀜) | "missing"(없어짐) | "messy"(어질러짐)
- size: "big"(방에 들어서자마자 눈에 띄는 큰 변화) | "small"(자세히 봐야 보이는 변화)
- x, y, w, h: 두 번째(오늘) 사진 기준 위치. 0~1 비율 (왼쪽 위가 0,0). 없어진 물건은 원래 있던 자리.

summary: 전체 총평 한 줄 ({name} 말투). 달라진 게 없으면 items는 빈 배열, summary는 칭찬.
closing: 다 찝고 나서 마지막에 한숨 쉬며 하는 마무리 잔소리 한 줄 ({name} 말투, 맵기 {spice}단계). 이런 느낌: {cl}. 깨끗하면 칭찬 한 줄.
score: 정리 상태 점수 0~100 정수. 평소 사진 상태가 100점. 많이 어질러질수록 낮게."""


def image_block(data: bytes, media_type: str) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(data).decode("utf-8"),
        },
    }


def inspect(baseline: bytes, base_type: str, today: bytes, today_type: str, voice: str, spice: int, mode: str) -> dict:
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        # 안전 필터가 거절하면 서버에서 다른 모델로 자동 재시도
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": RESULT_SCHEMA},
        },
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "평소 사진:"},
                    image_block(baseline, base_type),
                    {"type": "text", "text": "오늘 사진:"},
                    image_block(today, today_type),
                    {"type": "text", "text": build_prompt(voice, spice, mode)},
                ],
            }
        ],
    )
    if response.stop_reason == "refusal":
        raise HTTPException(422, "이 사진은 분석할 수 없어요.")
    text = next((b.text for b in response.content if b.type == "text"), "")
    return json.loads(text)


app = FastAPI(title="잔소리 탐지기")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 5 * 1024 * 1024


@app.post("/api/inspect")
async def api_inspect(
    baseline: UploadFile = File(...),
    today: UploadFile = File(...),
    voice: str = Form("ajumma"),
    spice: int = Form(2),
    mode: str = Form("mom"),
):
    """mode: obsess(강박) / mom(엄마) / dad(아빠).
    아빠모드에서 작은 변화 절반을 놓치는 건 앱(web/index.html applyMode)에서 처리."""
    files = []
    for f in (baseline, today):
        data = await f.read()
        media_type = f.content_type or "image/jpeg"
        if media_type not in ALLOWED:
            raise HTTPException(400, "사진 파일만 올릴 수 있어요.")
        if len(data) > MAX_BYTES:
            raise HTTPException(400, "사진이 너무 커요 (5MB 이하).")
        files.append((data, media_type))

    try:
        return inspect(files[0][0], files[0][1], files[1][0], files[1][1], voice, max(1, min(3, spice)), mode if mode in MODES else "mom")
    except anthropic.RateLimitError:
        raise HTTPException(429, "잠시 뒤에 다시 시도해주세요.")
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"AI 서버 오류 ({e.status_code})")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "AI 서버에 연결하지 못했어요.")


# ---------- 목소리 (ElevenLabs) ----------
ELEVEN_URL = "https://api.elevenlabs.io/v1"
ELEVEN_MODEL = "eleven_multilingual_v2"  # 한국어 지원. 더 새 모델이 있으면 바꾸기
AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/aac",
               "audio/wav", "audio/x-wav", "audio/webm", "audio/ogg"}
MAX_AUDIO = 10 * 1024 * 1024


def eleven_key() -> str | None:
    return os.environ.get("ELEVENLABS_API_KEY")


def persona_voice(persona: str) -> str | None:
    return os.environ.get(f"ELEVENLABS_VOICE_{persona.upper()}")


# 캐릭터별 말투 느낌 (stability 낮을수록 감정 기복이 큼)
VOICE_SETTINGS = {
    "ajumma": {"stability": 0.3, "similarity_boost": 0.8, "style": 0.7},
    "halmeoni": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.5},
    "ajeossi": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.5},
    "kid": {"stability": 0.3, "similarity_boost": 0.75, "style": 0.8},
}


@app.post("/api/tts")
async def api_tts(text: str = Form(...), persona: str = Form("ajumma"), voice_id: str = Form("")):
    """잔소리 한 줄을 mp3로. voice_id(복제한 목소리)가 있으면 그걸, 없으면 캐릭터 기본 목소리."""
    key = eleven_key()
    vid = voice_id or persona_voice(persona)
    if not key or not vid:
        raise HTTPException(503, "목소리 서버가 설정되지 않았어요.")
    if len(text) > 300:
        raise HTTPException(400, "문장이 너무 길어요.")
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{ELEVEN_URL}/text-to-speech/{vid}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": key},
            json={"text": text, "model_id": ELEVEN_MODEL,
                  "voice_settings": VOICE_SETTINGS.get(persona, VOICE_SETTINGS["ajumma"])},
        )
    if r.status_code != 200:
        raise HTTPException(502, f"목소리 생성 실패 ({r.status_code})")
    return Response(content=r.content, media_type="audio/mpeg")


@app.post("/api/voice-clone")
async def api_voice_clone(sample: UploadFile = File(...), consent: bool = Form(False), name: str = Form("잔소리 목소리")):
    """목소리 샘플(30초~1분)로 ElevenLabs 목소리를 만들고 voice_id를 돌려준다.
    본인이거나 허락받은 목소리만 (consent 필수)."""
    key = eleven_key()
    if not key:
        raise HTTPException(503, "목소리 서버가 설정되지 않았어요.")
    if not consent:
        raise HTTPException(400, "목소리 주인의 허락이 필요해요.")
    data = await sample.read()
    media_type = sample.content_type or "audio/mpeg"
    if media_type not in AUDIO_TYPES:
        raise HTTPException(400, "음성 파일만 올릴 수 있어요.")
    if len(data) > MAX_AUDIO:
        raise HTTPException(400, "파일이 너무 커요 (10MB 이하).")
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(
            f"{ELEVEN_URL}/voices/add",
            headers={"xi-api-key": key},
            data={"name": name[:50], "remove_background_noise": "true"},
            files={"files": (sample.filename or "voice.m4a", data, media_type)},
        )
    if r.status_code != 200:
        raise HTTPException(502, f"목소리 만들기 실패 ({r.status_code})")
    return {"voice_id": r.json().get("voice_id")}


@app.get("/health")
def health():
    has_key = bool(eleven_key())
    return {
        "ok": True,
        # tts: 캐릭터 기본 목소리가 설정돼 있음 / clone: 목소리 복제 가능
        "tts": has_key and any(persona_voice(p) for p in PERSONAS),
        "clone": has_key,
    }
