"""상대가 연락이 없을 때 안심시키는 멘트를 만든다.

ANTHROPIC_API_KEY 가 있으면 Claude 로 상황(시간대, 요일, 상대 상태, 평소 연락 패턴)을
보고 한두 문장을 만들고, 없거나 실패하면 규칙 기반 멘트로 대신한다.
"""
from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger(__name__)

MODEL = os.environ.get("YEONRAK_MODEL", "claude-opus-5-5")
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

SYSTEM_PROMPT = """너는 '연락각' 앱의 안심 도우미야.
사용자가 소중한 사람(연인, 배우자, 가족, 친구)에게서 한동안 연락을 못 받아 조금 불안한 상태야.
주어진 상황(현재 시각, 요일, 마지막 연락 이후 시간, 상대가 남긴 상태, 상대의 평소 연락 시간대)을 보고
상대가 왜 연락이 없는지 그럴듯하고 따뜻한 추측을 친근한 한국어 '~요' 체로 1~2문장만 말해줘.

규칙:
- 단정하지 말고 "아마", "~인가 봐요" 처럼 추측으로 말해.
- 가볍고 유머 있게. 예: "금요일 밤 11시예요. 아마 술 한잔하느라 폰 볼 틈이 없나 봐요 🍻"
- 사고, 바람, 아픔 같은 불안을 키우는 추측은 절대 하지 마.
- 마지막 연락 후 아주 오래(48시간 이상) 지났다면, 안심 멘트 뒤에 먼저 가볍게 연락해보라고 한마디 덧붙여.
- 이모지는 최대 1개. 따옴표나 머리말 없이 멘트만 출력해."""


@dataclass
class Situation:
    their_name: str          # 내가 상대를 부르는 이름 (예: 여친, 엄마)
    relation: str            # dating / spouse / parent / child / friend
    now: datetime            # 현지 시각
    hours_since: float       # 마지막 연락 이후 경과 시간
    their_status: str | None = None
    usual_hours: list[int] = field(default_factory=list)  # 상대가 평소 연락하는 시(hour)들, 많은 순

    def describe(self) -> str:
        lines = [
            f"상대: {self.their_name} (관계: {self.relation})",
            f"현재 시각: {self.now:%Y-%m-%d} {WEEKDAYS[self.now.weekday()]}요일 {self.now:%H:%M}",
            f"마지막 연락 이후: {self.hours_since:.1f}시간",
        ]
        if self.their_status:
            lines.append(f"상대가 남긴 상태: {self.their_status}")
        if self.usual_hours:
            hrs = ", ".join(f"{h}시" for h in self.usual_hours[:3])
            lines.append(f"상대가 평소 주로 연락하는 시간대: {hrs}")
        return "\n".join(lines)


def reassure(sit: Situation) -> dict:
    """{"message": str, "source": "ai" | "rule"} 를 돌려준다."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        try:
            msg = _ask_claude(sit)
            if msg:
                return {"message": msg, "source": "ai"}
        except Exception:  # 네트워크/키 문제 등은 규칙 기반으로 대체
            log.exception("Claude 호출 실패, 규칙 기반 멘트로 대체")
    return {"message": rule_based(sit), "source": "rule"}


def _ask_claude(sit: Situation) -> str | None:
    import anthropic

    client = anthropic.Anthropic(max_retries=1, timeout=30.0)
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=1024,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # 안전 분류기가 거절하면 서버가 다른 모델로 재시도
        output_config={"effort": "low"},  # 짧은 한두 문장이라 낮은 effort 로 충분
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": sit.describe()}],
    )
    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or None


def rule_based(sit: Situation, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    h, wd = sit.now.hour, sit.now.weekday()
    name = sit.their_name
    # 금·토 밤 8시~새벽 1시 (토요일 0시대는 금요일 밤, 일요일 0시대는 토요일 밤)
    weekend_night = (wd == 4 and h >= 20) or (wd == 5 and (h >= 20 or h < 1)) or (wd == 6 and h < 1)

    if sit.their_status:
        s = sit.their_status
        if any(k in s for k in ("회식", "술", "모임", "파티")):
            msg = f"{name} 지금 '{s}'래요. 아마 떠드느라 정신이 없나 봐요 🍻"
        elif any(k in s for k in ("운동", "헬스", "러닝", "수영")):
            msg = f"{name} '{s}' 중이래요. 땀 흘리느라 폰은 사물함에 있을 거예요 💪"
        elif any(k in s for k in ("회의", "일", "근무", "야근", "수업")):
            msg = f"{name} '{s}' 중이래요. 끝나면 연락 올 거예요."
        elif any(k in s for k in ("잠", "자", "취침")):
            msg = f"{name} '{s}'래요. 푹 자고 일어나면 연락 올 거예요 😴"
        else:
            msg = f"{name} 상태가 '{s}'예요. 그거 하느라 바쁜가 봐요."
    elif 1 <= h < 7:
        msg = rng.choice([
            f"새벽 {h}시예요. {name} 아마 꿀잠 자는 중일 거예요 😴",
            f"지금 새벽이라 {name} 자고 있을 확률 99%예요.",
        ])
    elif weekend_night:
        msg = rng.choice([
            f"{WEEKDAYS[wd]}요일 밤 {h}시예요. 아마 술 한잔하느라 폰 볼 틈이 없나 봐요 🍻",
            f"주말 밤이잖아요. {name} 떠드느라 정신이 없나 봐요.",
        ])
    elif wd < 5 and 12 <= h < 13:
        msg = f"점심시간이에요. {name} 밥 먹으면서 수다 떠는 중인가 봐요 🍚"
    elif wd < 5 and 9 <= h < 18:
        msg = rng.choice([
            f"평일 {h}시, 한창 일할 시간이에요. {name} 바빠서 그런가 봐요.",
            f"지금 업무 시간이라 {name} 폰 볼 여유가 없나 봐요 💼",
        ])
    elif 18 <= h < 20:
        msg = f"퇴근길이거나 저녁 먹을 시간이에요. {name} 곧 연락 올 거예요."
    elif 20 <= h or h < 1:
        msg = f"저녁 시간이라 {name} 씻거나 쉬는 중인가 봐요. 조금만 기다려봐요."
    else:
        msg = f"{name} 아침 준비하느라 정신없나 봐요 ☀️"

    if sit.usual_hours and not sit.their_status:
        nxt = _next_usual_hour(h, sit.usual_hours)
        if nxt is not None and nxt != h:
            msg += f" 보통 {nxt}시쯤 연락하더라고요."
    if sit.hours_since >= 48:
        msg += " 그래도 꽤 됐으니 먼저 가볍게 연락해봐요."
    return msg


def _next_usual_hour(now_hour: int, usual: list[int]) -> int | None:
    later = sorted(usual[:3], key=lambda u: (u - now_hour) % 24)
    return later[0] if later else None
