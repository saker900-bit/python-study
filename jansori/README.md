# 빠직! 잔소리 탐지기

방의 평소 사진을 등록해 두고 오늘 사진을 찍으면, 달라진 곳을 찾아서
뽀글머리 몸빼 아줌마가 이마에 빠직 표시를 띄우고 손가락으로 찝으며 잔소리해 주는 앱.

## 지금 되는 것 (1일차, 폰에서 만든 것)

- 방별 평소 사진 등록 (거실/안방/작은방/주방/현관 + 방 추가), 폰 안에 저장
- 오늘 사진 찍기 → 비교 → 달라진 곳에 빨간 박스
- 캐릭터가 박스 쪽으로 이동해서 팔을 돌려 손가락으로 가리킴 + 빠직 표시 + 화면 흔들림 + "지직" 효과음
- 잔소리 음성 (폰 기본 음성 합성, 음높이·속도로 목소리 느낌을 냄)
- 캐릭터 4종: 아줌마 / 할머니 / 아저씨 / 어린아이 (생김새, 목소리 따로 고를 수 있음)
- 얼굴 사진 올리면 캐릭터 얼굴이 그 사람으로 바뀜 (뽀글머리는 그대로)
- 맵기 3단계 (순한맛/보통맛/매운맛)
- 눈썰미 3단계: 강박모드(다 찾음) / 엄마모드(보통) / 아빠모드(작은 건 반은 못 봄)
- 다 찝고 나면 마무리 잔소리 ("으휴~ 이래서 내가 집을 비울 수가 없어~") → 두구두구 둥! 정리 점수 (100점 만점)
- 내 목소리로 잔소리 (ElevenLabs 목소리 복제, 서버 연결 버전에서만)
- 광고: 첫 검사는 무료, 새 사진으로 다시 검사하면 전면 광고 (5초 뒤 닫기). 2,900원 한 번 결제로 광고 평생 제거 + 구매 복원
  (웹 버전은 테스트 광고/테스트 결제, 돈 안 나감)
- 분석은 세 가지 방법 중 되는 걸로:
  1. Claude 앱 안에서 열면 Claude가 직접 사진 비교 (AI 검사)
  2. `window.JANSORI_API` 에 서버 주소가 있으면 내 서버로 비교 (스토어 앱용)
  3. 둘 다 없으면 픽셀 비교로 대충 찾기 (간단 비교 모드)

## 플레이스토어 출시

순서는 [PLAYSTORE_GUIDE.md](PLAYSTORE_GUIDE.md), 스토어에 붙여넣을 글은 [store/listing.md](store/listing.md).

## 폴더

```
jansori/
  web/index.html     앱 화면 전체 (HTML 한 파일)
  server/main.py     AI 비교 서버 (FastAPI + Claude API)
  server/requirements.txt
  server/privacy.html  개인정보처리방침 (서버 /privacy)
  app/               안드로이드 앱 (Capacitor). src/config.js 에 서버 주소·광고·결제 키
  store/             스토어 아이콘, 그래픽, 스크린샷, 설명글
```

## 서버 실행 (PC)

```bash
cd jansori/server
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --reload --port 8000
```

그다음 `web/index.html` 의 `<script>` 위에
`<script>window.JANSORI_API = "http://localhost:8000";</script>` 한 줄 넣고 브라우저로 열면 됨.

## PC에서 Claude Code로 할 일 (스토어까지)

1. **앱으로 감싸기**: Capacitor 로 `web/` 을 그대로 안드로이드/iOS 앱으로 만들기
   (`npm i @capacitor/core @capacitor/cli`, `npx cap init`, `npx cap add android`, `npx cap add ios`).
   카메라는 `@capacitor/camera` 플러그인으로 바꾸면 더 매끄러움.
2. **서버 배포**: `server/` 를 Cloud Run, Fly.io, Render 같은 곳에 올리고 앱에 주소 넣기.
   API 키는 절대 앱 안에 넣지 말 것. 남용 막으려고 하루 횟수 제한 추가 필요.
3. **목소리 (ElevenLabs)**: 서버에 이미 만들어 둠 (`/api/tts`, `/api/voice-clone`). 아직 실제 키로는 안 돌려봄.
   - ElevenLabs 가입 → API 키 발급 → `ELEVENLABS_API_KEY` 환경변수
   - ElevenLabs 보이스 라이브러리에서 아줌마/할머니/아저씨/아이 느낌 한국어 목소리 골라서
     `ELEVENLABS_VOICE_AJUMMA` 같은 환경변수에 voice_id 넣기
   - 목소리 복제(샘플 올리기)는 ElevenLabs 유료 요금제가 필요할 수 있음. 요금제 확인할 것
   - 같은 대사는 매번 새로 만들지 말고 서버에 캐시하면 비용 절약
   - API 주소/모델 이름은 ElevenLabs 문서에서 한 번 확인 (`eleven_multilingual_v2` 사용 중)
4. **광고 + 광고 제거 결제 (진짜로 연결)**
   - 광고: AdMob 가입 → 전면 광고 단위 만들기 → `@capacitor-community/admob` 플러그인 설치 →
     `window.JANSORI_ADMOB_ID` 에 광고 단위 ID 넣기 (앱은 `Capacitor.Plugins.AdMob` 이 있으면 자동으로 씀.
     플러그인 함수 이름 `prepareInterstitial` / `showInterstitial` 은 설치한 버전 문서로 확인)
   - 결제: 앱 안에서 파는 디지털 상품이라 **구글 플레이 결제 / 애플 인앱결제를 써야 함** (외부 결제 쓰면 심사 거절)
     - 두 스토어 콘솔에 비소모성 상품 `remove_ads_forever`, 2,900원 등록
     - RevenueCat 같은 서비스를 쓰면 두 스토어를 한 번에 처리하기 쉬움
     - `window.JANSORI_STORE = { buy(id), restore(id) }` 를 만들어서 연결 (둘 다 성공하면 true)
     - 애플은 '구매 복원' 버튼이 필수 (이미 있음)
   - 지금은 결제 여부를 폰에만 저장함. 진짜 버전은 앱 켤 때마다 스토어에서 구매 내역 확인하기
   - 스토어 수수료(보통 15~30%) 빼면 실제로 받는 돈은 2,900원보다 적음
5. **얼굴 바꾸기 업그레이드**: 지금은 사진을 동그랗게 잘라 붙이는 방식.
   이미지 생성 AI로 업로드한 얼굴을 만화풍 캐릭터로 바꾸는 기능 추가 가능.
6. **스토어 심사 대비**
   - 개인정보처리방침 페이지 (방 사진, 얼굴 사진을 서버로 보낸다는 것, 저장 안 한다는 것)
   - 얼굴 사진 올릴 때 "본인이거나 허락받은 사람 사진만" 안내
   - 안드로이드: 구글 플레이 개발자 계정 (1회 $25), iOS: 애플 개발자 프로그램 (연 $99, 맥 필요)
7. **재미 기능 아이디어**: 잔소리 점수/연속 깨끗한 날 기록, 결과 화면 공유 이미지, 매일 정해진 시간 "검사 알림"
