import os

def _f(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

DB_PATH = _f("DB_PATH", "subway.db")
POLL_SECONDS = int(_f("POLL_SECONDS", "45"))
# 이 시간보다 오래된 글은 무시 (옛날 기사로 알림 쏘는 것 방지)
MAX_POST_AGE_MIN = int(_f("MAX_POST_AGE_MIN", "90"))
# 이만큼 새 소식이 없으면 조용히 종료 처리 (복구 알림은 안 보냄)
INCIDENT_TTL_MIN = int(_f("INCIDENT_TTL_MIN", "180"))
# 푸시 발송 기준 점수: 뉴스 1건=2점, 공식 계정=3점, SNS 1건=1점
PUSH_THRESHOLD = int(_f("PUSH_THRESHOLD", "2"))

NAVER_CLIENT_ID = _f("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = _f("NAVER_CLIENT_SECRET")
X_BEARER_TOKEN = _f("X_BEARER_TOKEN")
IG_USER_ID = _f("IG_USER_ID")
IG_ACCESS_TOKEN = _f("IG_ACCESS_TOKEN")

EXPO_ACCESS_TOKEN = _f("EXPO_ACCESS_TOKEN")  # 선택: Expo 푸시 보안 강화 시
REVENUECAT_WEBHOOK_AUTH = _f("REVENUECAT_WEBHOOK_AUTH")
ENTITLEMENT_ID = _f("ENTITLEMENT_ID", "premium")
# 개발용: 앱이 가짜 결제(mock_ 아이디)일 때도 푸시 허용
DEV_MODE = _f("DEV_MODE", "0") == "1"
RUN_WORKER = _f("RUN_WORKER", "1") == "1"
