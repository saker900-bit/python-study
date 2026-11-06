import time
from datetime import datetime, timezone

from app.engine import Engine
from app.push import format_notice
from app.sources.base import Post
from app.store import Store


def post(text, kind="news", uid=None, minutes_ago=1):
    ts = datetime.fromtimestamp(time.time() - minutes_ago * 60, timezone.utc)
    uid = uid or str(hash((text, kind)))
    return Post(kind, uid, text, f"https://e.com/{uid}", ts)


def test_delay_then_resolve():
    e = Engine(Store(":memory:"))
    n = e.process([post("2호선 강남역 스크린도어 고장으로 열차 지연")])
    assert [x.kind for x in n] == ["delay"]
    assert format_notice(n[0]) == ("🚨 2호선 강남역 지연", "스크린도어 고장(으)로 열차 운행이 지연되고 있어요.")
    # 같은 사건 다른 기사 → 추가 알림 없음
    assert e.process([post("[속보] 2호선 강남역 스크린도어 고장…출근길 지연")]) == []
    n = e.process([post("2호선 강남역 스크린도어 복구 완료, 정상 운행")])
    assert [x.kind for x in n] == ["resolved"]
    assert e.recent()[0]["status"] == "resolved"
    assert len(e.recent()[0]["sources"]) == 3


def test_single_sns_post_waits_for_confirmation():
    e = Engine(Store(":memory:"))
    assert e.process([post("1호선 구로역 열차 고장으로 멈춰있음", kind="x", uid="a")]) == []
    n = e.process([post("1호선 구로역 열차 고장 지연 실화냐", kind="x", uid="b")])
    assert [x.kind for x in n] == ["delay"]


def test_old_posts_and_duplicates_ignored():
    e = Engine(Store(":memory:"))
    assert e.process([post("3호선 교대역 화재로 지연", uid="old", minutes_ago=600)]) == []
    p = post("3호선 교대역 화재로 지연")
    assert len(e.process([p])) == 1
    assert e.process([p]) == []


def test_recipients_filter_by_line_and_subscription():
    s = Store(":memory:")
    s.upsert_device("ExponentPushToken[a]", "u1", "ios", ["2"], True, True)
    s.upsert_device("ExponentPushToken[b]", "u2", "android", [], False, True)
    s.upsert_device("ExponentPushToken[c]", "u3", "android", [], True, True)  # 미구독
    s.set_subscriber("u1", time.time() + 1000)
    s.set_subscriber("u2", time.time() + 1000)
    assert sorted(s.recipients("2", resolved=False)) == ["ExponentPushToken[a]", "ExponentPushToken[b]"]
    assert s.recipients("4", resolved=False) == ["ExponentPushToken[b]"]
    assert s.recipients("2", resolved=True) == ["ExponentPushToken[a]"]
