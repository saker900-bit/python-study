"""글 하나를 읽고 '어느 노선 / 어느 역 / 무슨 이유로 지연(또는 복구)' 인지 뽑아낸다."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

from .lines import find_lines

# (표시 이름, 패턴) — 위에서부터 먼저 맞는 것 사용
CAUSES: list[tuple[str, str]] = [
    ("인명사고", r"인명\s*사고|투신|사상\s*사고|사망\s*사고|열차에\s*치|선로[로에]?\s*(?:뛰어|추락|떨어)"),
    ("화재", r"화재|불이\s*나|불길|불꽃|연기가?\s*(?:발생|나|피어)|타는\s*냄새"),
    ("스크린도어 고장", r"스크린\s*도어|안전문|PSD"),
    ("출입문 고장", r"출입문|(?:열차|차량)\s*문\s*(?:고장|이상|안\s*닫)"),
    ("응급환자 발생", r"(?:응급|위급)?\s*환자|쓰러[져진지]|의식을?\s*잃|심정지|구급"),
    ("선로 무단 진입", r"선로\s*(?:에\s*)?(?:무단|진입|들어가|사람|승객)"),
    ("신호 장애", r"신호\s*(?:장애|고장|오류|이상|설비)|신호기"),
    ("전력 장애", r"단전|정전|전력\s*(?:공급|장애|차단)|전차선|급전"),
    ("선로 장애", r"선로\s*(?:장애|고장|이상|결함|보수)|레일\s*(?:파손|균열|이상)|궤도|탈선"),
    ("차량 고장", r"(?:차량|열차|기관|기기|전동차|동력|제동)\s*(?:장치\s*)?(?:고장|결함|이상)|고장\s*열차"),
    ("비상정지", r"비상\s*(?:정지|제동|버튼|핸들|브레이크)"),
    ("승객 난동", r"난동|폭행|소란|흉기|칼부림|소동"),
    ("시위", r"시위|집회|전장연|탑승\s*투쟁"),
    ("기상 악화", r"폭설|폭우|침수|강풍|결빙|폭염|한파|태풍"),
]
_CAUSES = [(name, re.compile(p, re.IGNORECASE)) for name, p in CAUSES]

TRANSIT = re.compile(r"지하철|전철|호선|열차|전동차|승강장|코레일|서울교통공사|철도|선로|역\b|역[에의을이]|" +
                     r"신분당|수인분당|경의중앙|공항철도|GTX|골드라인|에버라인|경전철|우이신설|신림선|서해선|경춘선",
                     re.IGNORECASE)
DELAY = re.compile(r"지연|늦어|운행\s*(?:이\s*)?(?:중단|차질|지장|장애|정지|중지|불가|멈)|멈[춰춤췄추]|서행|"
                   r"무정차|운행이\s*(?:중단|멈)|운행을?\s*(?:중단|멈)|(?:출근|퇴근)\s*대란|열차가?\s*(?:멈|정지|서\s*있)|"
                   r"끊겼|올\s*스톱|안\s*와|안\s*옴")
RESOLVED = re.compile(r"운행\s*(?:이\s*)?재개|운행을?\s*재개|정상\s*운행|정상화|정상\s*운영|복구\s*(?:완료|됐|되었|돼|되어)|"
                      r"재개\s*(?:됐|되었|돼|했)|운행\s*정상|다시\s*(?:운행|다니|움직)")
# 사건 보도가 아닌 글(정책, 통계, 보상 등)은 버린다
NOISE = re.compile(r"국정감사|국감|예산|공약|통계|지난해|작년|연간|보상\s*기준|입찰|채용|요금\s*인상|"
                   r"(?:지난|어제|그제)\s*\d*\s*(?:일|주|달)|개통\s*(?:지연|연기)|공사\s*지연|착공")

_STATION = re.compile(r"(?<![가-힣])([가-힣]{2,8})역(?![가-힣])|(?<![가-힣])([가-힣]{2,8})역(?=에서|서|에|을|를|은|는|이|과|와|으로|부근|인근|사이|구간|방면|방향|쪽)")
_RANGE = re.compile(r"(?<![가-힣])([가-힣]{2,8})(?:역)?\s*[~\-–]\s*([가-힣]{2,8})역")
STOP_STATIONS = {"지하철", "전철", "해당", "인근", "다음", "일부", "모든", "주요", "여러", "전체", "이전", "무정차",
                 "도착", "출발", "정차", "기차", "환승", "종착", "시발", "광역", "철도", "열차", "각", "주변", "근처",
                 "인접", "역사", "반대", "출구"}


@dataclass
class Detection:
    kind: str  # "delay" | "resolved"
    lines: list[str]
    station: str | None
    cause: str
    text: str

    @property
    def line(self) -> str | None:
        return self.lines[0] if self.lines else None


def clean(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def find_station(text: str) -> str | None:
    m = _RANGE.search(text)
    if m and m.group(1) not in STOP_STATIONS:
        return m.group(1)
    for m in _STATION.finditer(text):
        name = m.group(1) or m.group(2)
        if len(name) >= 2 and name not in STOP_STATIONS:
            return name
    return None


def find_cause(text: str) -> str:
    for name, rx in _CAUSES:
        if rx.search(text):
            return name
    return "운행 장애"


def parse(raw: str) -> Detection | None:
    text = clean(raw)
    if not text or not TRANSIT.search(text) or NOISE.search(text):
        return None
    resolved = bool(RESOLVED.search(text))
    delayed = bool(DELAY.search(text))
    if not (resolved or delayed):
        return None
    lines = find_lines(text)
    station = find_station(text)
    if not lines and not station:
        return None  # 어디인지 모르면 알림 가치가 없음
    return Detection(
        kind="resolved" if resolved else "delay",
        lines=lines,
        station=station,
        cause=find_cause(text),
        text=text,
    )
