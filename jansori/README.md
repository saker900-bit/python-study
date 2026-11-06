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
- 분석은 세 가지 방법 중 되는 걸로:
  1. Claude 앱 안에서 열면 Claude가 직접 사진 비교 (AI 검사)
  2. `window.JANSORI_API` 에 서버 주소가 있으면 내 서버로 비교 (스토어 앱용)
  3. 둘 다 없으면 픽셀 비교로 대충 찾기 (간단 비교 모드)

## 폴더

```
jansori/
  web/index.html     앱 화면 전체 (HTML 한 파일)
  server/main.py     AI 비교 서버 (FastAPI + Claude API)
  server/requirements.txt
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
3. **목소리 업그레이드**: 지금은 폰 기본 음성이라 할머니/아이 느낌이 약함.
   한국어 캐릭터 음성 TTS 서비스(예: Typecast, CLOVA Voice, ElevenLabs)로 서버에서 음성 파일 만들어 보내기.
   또는 "이거 뭐야!" "이거 치워!" 같은 고정 대사는 직접 녹음해서 넣기.
4. **얼굴 바꾸기 업그레이드**: 지금은 사진을 동그랗게 잘라 붙이는 방식.
   이미지 생성 AI로 업로드한 얼굴을 만화풍 캐릭터로 바꾸는 기능 추가 가능.
5. **스토어 심사 대비**
   - 개인정보처리방침 페이지 (방 사진, 얼굴 사진을 서버로 보낸다는 것, 저장 안 한다는 것)
   - 얼굴 사진 올릴 때 "본인이거나 허락받은 사람 사진만" 안내
   - 안드로이드: 구글 플레이 개발자 계정 (1회 $25), iOS: 애플 개발자 프로그램 (연 $99, 맥 필요)
6. **재미 기능 아이디어**: 잔소리 점수/연속 깨끗한 날 기록, 결과 화면 공유 이미지, 매일 정해진 시간 "검사 알림"
