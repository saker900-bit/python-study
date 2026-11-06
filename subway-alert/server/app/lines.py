"""노선 이름 인식. id 는 앱 src/lib/lines.ts 와 같아야 한다."""
import re

# 순서 중요: 긴/구체적인 이름을 먼저 검사 (인천1호선 이 1호선 으로 잡히지 않게)
LINE_PATTERNS: list[tuple[str, str]] = [
    ("incheon1", r"인천\s*(?:지하철\s*)?1\s*호선"),
    ("incheon2", r"인천\s*(?:지하철\s*)?2\s*호선"),
    ("shinbundang", r"신분당선?"),
    ("suinbundang", r"수인\s*·?\s*분당선|수인분당|(?<!신)분당선|수인선"),
    ("gyeongui", r"경의\s*·?\s*중앙선|경의중앙|경의선|(?<![가-힣])중앙선"),
    ("airport", r"공항철도|AREX|공철"),
    ("gyeongchun", r"경춘선"),
    ("seohae", r"서해선"),
    ("gtxa", r"GTX\s*-?\s*A"),
    ("uisinseol", r"우이\s*신설선?"),
    ("sillim", r"신림선"),
    ("gimpo", r"김포\s*골드라인|골드라인"),
    ("everline", r"에버라인"),
    ("uijeongbu", r"의정부\s*경전철"),
]
LINE_PATTERNS += [(str(n), rf"(?<![0-9가-힣]){n}\s*호선") for n in range(1, 10)]

_COMPILED = [(lid, re.compile(p, re.IGNORECASE)) for lid, p in LINE_PATTERNS]


def find_lines(text: str) -> list[str]:
    """본문에 언급된 노선 id 목록 (등장 순서)."""
    hits: list[tuple[int, str]] = []
    taken: list[tuple[int, int]] = []
    for lid, rx in _COMPILED:
        for m in rx.finditer(text):
            if any(s <= m.start() < e for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            hits.append((m.start(), lid))
    seen: list[str] = []
    for _, lid in sorted(hits):
        if lid not in seen:
            seen.append(lid)
    return seen


LINE_NAMES = {
    "1": "1호선", "2": "2호선", "3": "3호선", "4": "4호선", "5": "5호선",
    "6": "6호선", "7": "7호선", "8": "8호선", "9": "9호선",
    "shinbundang": "신분당선", "suinbundang": "수인분당선", "gyeongui": "경의중앙선",
    "airport": "공항철도", "gyeongchun": "경춘선", "seohae": "서해선", "gtxa": "GTX-A",
    "incheon1": "인천1호선", "incheon2": "인천2호선", "uisinseol": "우이신설선",
    "sillim": "신림선", "gimpo": "김포골드라인", "everline": "용인에버라인",
    "uijeongbu": "의정부경전철",
}
