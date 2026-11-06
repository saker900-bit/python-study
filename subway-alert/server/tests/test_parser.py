import pytest

from app.parser import parse

CASES = [
    ("2호선 강남역 스크린도어 고장으로 열차 운행이 지연되고 있습니다", "delay", "2", "강남", "스크린도어 고장"),
    ("[속보] 지하철 1호선 구로역서 응급환자 발생…열차 지연", "delay", "1", "구로", "응급환자 발생"),
    ("4호선 사당역 인근 화재로 상하행 열차 무정차 통과", "delay", "4", "사당", "화재"),
    ("신분당선 판교역 차량 고장으로 운행 차질", "delay", "shinbundang", "판교", "차량 고장"),
    ("인천1호선 부평역 신호 장애로 지연 운행 중", "delay", "incheon1", "부평", "신호 장애"),
    ("수인분당선 선릉역 열차 고장 지연, 30분 넘게 멈춰있음", "delay", "suinbundang", "선릉", "차량 고장"),
    ("경의중앙선 운행 지연 중… 원인은 확인 중", "delay", "gyeongui", None, "운행 장애"),
    ("2호선 강남역 스크린도어 복구 완료, 정상 운행 중입니다", "resolved", "2", "강남", "스크린도어 고장"),
    ("1호선 구로역 열차 운행 재개", "resolved", "1", "구로", "운행 장애"),
    ("7호선 대림~남구로역 구간 선로 장애로 운행 중단", "delay", "7", "대림", "선로 장애"),
    ("5호선 광화문역에서 전장연 시위로 열차 지연", "delay", "5", "광화문", "시위"),
]


@pytest.mark.parametrize("text,kind,line,station,cause", CASES)
def test_detects(text, kind, line, station, cause):
    d = parse(text)
    assert d is not None, text
    assert d.kind == kind
    assert d.line == line
    assert d.station == station
    assert d.cause == cause


@pytest.mark.parametrize("text", [
    "오늘 점심 강남역 맛집 추천",
    "지하철 9호선 4단계 연장 공사 지연…개통 2028년으로",
    "국정감사서 지하철 지연 통계 공개",
    "수도권 지역에 비가 옵니다",
    "회의가 지연되고 있다",
])
def test_ignores(text):
    assert parse(text) is None
