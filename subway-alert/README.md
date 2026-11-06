# 지하철 지연알림 🚇🔔

어느 노선·어느 역이든 지연이 생기면 바로 푸시. 복구되면 복구 알림도.
월 2,900원 / 연 24,360원(30% 할인) · 첫 달 무료.

```
app/     모바일 앱 (Expo / React Native, iOS + Android 한 번에)
server/  지연 감지 서버 (Python / FastAPI) — 뉴스·SNS 감시 → 푸시 발송
```

## 동작 방식

1. 서버가 45초마다 구글 뉴스 RSS · 네이버 뉴스 · X · 인스타그램에서 지하철 관련 글을 수집
2. `parser.py` 가 글에서 **노선 / 역 / 사유**(환자 발생, 스크린도어·차량·신호 고장, 화재, 인명사고, 시위 등 14종)와 **지연/복구 여부**를 뽑아냄
3. 같은 사건은 하나로 묶고, 신뢰도 점수(뉴스 2, SNS 1, 공식 3)가 2점 이상이면 푸시
   → SNS 글 하나만으로는 오보일 수 있어서 한 건 더 확인되면 발송
4. "운행 재개 / 정상 운행 / 복구 완료" 글이 잡히면 ✅ 복구 알림
5. 구독 중이고, 그 노선을 고른 사람에게만 발송

## 지금 바로 폰에서 확인 (결제 없이 개발 모드)

```bash
cd server && pip install -r requirements.txt
DEV_MODE=1 uvicorn app.main:app --host 0.0.0.0 --port 8000

cd app && npm install
EXPO_PUBLIC_API_URL=http://<내 PC IP>:8000 npx expo start
```
RevenueCat 키가 없으면 앱이 **가짜 결제 모드**로 돌아서 구독 흐름을 끝까지 눌러볼 수 있음.
(푸시·결제 모듈 때문에 Expo Go 대신 개발 빌드 필요: `npx eas-cli build --profile development`)

## 스토어 출시 체크리스트

### 1. 계정
- [ ] Apple Developer ($99/년), Google Play Console ($25 1회)
- [ ] Expo 계정 → `cd app && npx eas-cli init` (projectId 자동 기록)
- [ ] `app.json` 의 `com.yourname.subwayalert` 를 내 번들 ID 로 변경, 아이콘 교체

### 2. 구독 상품 (스토어 콘솔에서 만듦)
| 상품 ID | 가격 | 무료체험 |
|---|---|---|
| `subway_monthly` | ₩2,900 / 1개월 | 1개월 무료 (신규 사용자 혜택) |
| `subway_yearly`  | ₩24,360 / 1년 | 1개월 무료 |

- App Store Connect: 구독 그룹 1개에 두 상품, "도입 혜택 → 무료 → 1개월"
- Play Console: 구독 2개, 각 기본 요금제에 "무료 체험 1개월" 혜택
- 결제수단 등록·자동결제 동의는 **스토어 결제창이 처리** (앱 안에서 카드 받으면 심사 거절됨)

### 3. RevenueCat (무료, 월 매출 $2.5k까지)
- [ ] 앱 2개(iOS/Android) 등록 → 상품 연결 → Entitlement `premium` 에 두 상품 붙이기
- [ ] Offering `default` 에 Monthly / Annual 패키지
- [ ] Webhook: `https://<서버>/v1/webhooks/revenuecat`, Authorization = `REVENUECAT_WEBHOOK_AUTH`
- [ ] 앱 `.env` 에 `EXPO_PUBLIC_RC_IOS_KEY`, `EXPO_PUBLIC_RC_ANDROID_KEY`

### 4. 서버 배포
Fly.io / Railway / Render 아무거나. 프로세스 하나로 API + 수집기 동시 실행.
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
디스크(볼륨)를 붙이고 `DB_PATH` 를 거기로.

### 5. 심사용
- [ ] 이용약관 · 개인정보처리방침 페이지 → `EXPO_PUBLIC_TERMS_URL`, `EXPO_PUBLIC_PRIVACY_URL`
- [ ] 스크린샷 (피드 / 페이월 / 설정)
- [ ] 빌드 & 제출: `npx eas-cli build -p all --profile production` → `npx eas-cli submit -p all`

## 데이터 소스

| 소스 | 비용 | 상태 |
|---|---|---|
| 구글 뉴스 RSS | 무료, 키 불필요 | 기본 켜짐 |
| 네이버 뉴스 검색 API | 무료 (일 25,000회) | 키 넣으면 켜짐 — **강력 추천** |
| X 최근 검색 API | 유료 (Basic 플랜 이상) | 키 넣으면 켜짐 |
| 인스타그램 Graph API | 무료지만 비즈니스 계정 + Meta 앱 심사 필요, 해시태그 7일 30개 제한 | 키 넣으면 켜짐 |

## 주의

- 뉴스·SNS 기반이라 공식 안내보다 느리거나 틀릴 수 있음 → 앱/약관에 "참고용" 고지 필요
- 무료체험 → 유료 전환은 전자상거래법상 사전 고지 의무가 있음. 앱은 체험 종료 3일 전 알림을 띄우고
  페이월에 자동결제 동의 체크박스를 두었지만, 출시 전 최신 법령 기준 확인 권장
- 인스타·X 글을 앱에 그대로 노출하면 저작권/약관 이슈 → 지금은 출처 링크만 노출

## 테스트
```bash
cd server && python -m pytest -q   # 파서·사건 묶기·수신자 필터 20개
cd app && npx tsc --noEmit
```
