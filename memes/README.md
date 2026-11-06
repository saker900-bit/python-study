# 밈 탐정

기억나는 대로 밈을 설명하면 짤을 화면 가운데에 크게 띄우고 "이거 맞음?" 하고 물어보는 앱.
아니면 다음 후보, 맞으면 이름·출처·설명과 짤 저장 버튼.

## 돈 버는 구조

| 수익원 | 어떻게 | 비고 |
|---|---|---|
| AdMob 전면 광고 | 검색할 때마다 결과 전에 1번 | 광고 제거 결제자는 안 나옴 |
| KLIPY 결과 속 광고 | KLIPY가 짤 결과 사이에 광고를 끼워 주고 수익을 나눠 줌 | KLIPY 파트너 패널에서 광고 켜고 정산 |
| 광고 평생 제거 ₩2,900 | 1회 결제 (비소모성 `remove_ads`) | 결제자는 광고 끈 KLIPY 키로 전환 |

## 짤은 어디서 오나: KLIPY (스토어 앱)

- Tenor API는 2026년 6월 30일에 종료됨. GIPHY는 유료로 바뀜.
- **KLIPY**: 무료, 콘텐츠 라이선스 처리됨, 결과 속 광고로 수익 배분. Tenor에서 옮겨 온 앱들이 많이 씀.
  한국 짤이 얼마나 있는지는 **KLIPY 키를 받아서 확인해야 함** (아래 할 일 1번).
- 앱에는 우리가 직접 쓴 밈 정보(이름, 대사, 출처, 설명, KLIPY 검색어)만 들어 있고,
  짤은 앱이 KLIPY에서 그때그때 직접 받아 온다.

### KLIPY 규칙 (어기면 키 정지) — 코드에 이미 반영됨

- 검색창 기본 문구 "Search KLIPY" 필수 → 들어가 있음
- 화면에 "Powered by KLIPY" 표시 → 들어가 있음
- KLIPY 요청과 짤 로딩은 **사용자 기기에서 직접**. 내 서버를 거치면 안 됨 → 서버는 우리 텍스트 도감과 AI 검색만 함
- 짤을 내 서버에 저장·재호스팅 금지, 결과 순서 바꾸기·광고 빼기 금지 → KLIPY가 준 순서대로, 광고도 그 자리에 보여줌
- 광고 제거 결제자에게 광고 없는 결과를 주려면 KLIPY 파트너 패널에서 **광고 끈 키를 하나 더** 만들어 `KLIPY_KEY_NOADS` 로 넣기
- 사용자가 짤을 보내면 KLIPY share API 호출, 신고 버튼은 KLIPY report API 호출 → 들어가 있음
- 짤 저장 기능: 앱에서는 공유 창(카톡 보내기, 동영상 저장)으로 처리. 출시 전에 developers@klipy.com 에
  "사용자가 공유 창으로 기기에 저장하는 것" 괜찮은지 한 번 확인할 것

## 미리보기 버전 (Claude 아티팩트)

Claude 앱 안에서 보는 버전은 개인 테스트용이다. 아티팩트는 외부 API를 못 불러서 Tenor 짤 파일을 페이지 안에 넣어 둠.
**이 버전으로는 돈을 벌거나 공개 배포하면 안 됨** (짤 권리 문제). 광고·결제 버튼은 화면 확인용.

## 폴더

```
memes/
  catalog.json         밈 도감 (이름, 대사, 출처, 설명, 짤 주소)
  web/template.html    앱 화면 전체 (HTML 한 파일, 빌드할 때 도감이 들어감)
  server/main.py       검색 서버 (FastAPI + Claude API), 최신 도감 내려주기
  tools/build.py       화면 만들기 (artifact | app)
  tools/candidates.py  새 밈 짤 후보 찾기 + 확인용 시트
  tools/add_meme.py    고른 짤로 도감에 추가
  DAILY_UPDATE.md      매일 업데이트 절차
```

## 서버 실행 (PC)

```bash
cd memes/server
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --port 8000
```

앱 화면은 `python tools/build.py app` 으로 `site/index.html` 을 만들고,
`<script>` 위에 `<script>window.MEME_CONFIG = { api: "https://내서버주소" };</script>` 를 넣는다.
서버가 있으면 앱이 켜질 때 최신 도감을 받아오니까 매일 추가된 밈이 앱 업데이트 없이 반영된다.

## PC에서 Claude Code로 할 일 (스토어까지)

1. **KLIPY 키 받기**: partner.klipy.com 가입 → API Keys → 플랫폼 만들기 (광고 켠 키 1개, 광고 끈 키 1개).
   테스트 키는 시간당 100회. 다 되면 패널에서 Production 신청.
   빌드: `KLIPY_KEY=광고켠키 KLIPY_KEY_NOADS=광고끈키 MEME_API=https://내서버 python tools/build.py app`
2. **앱으로 감싸기**: Capacitor로 `site/` 를 안드로이드/iOS 앱으로
   (`npm i @capacitor/core @capacitor/cli`, `npx cap init`, `npx cap add android`, `npx cap add ios`).
   저장 기능용 `@capacitor/filesystem`, `@capacitor/share` 설치.
3. **광고 (AdMob)**: `@capacitor-community/admob` 설치. AdMob 가입 → 앱 등록 → 전면 광고 단위 2개 (안드로이드/iOS) 만들기.
   `web/template.html` 의 `ADMOB` 에 내 광고 단위 ID 넣고 `testing: false`.
   iOS는 앱 추적 동의(ATT) 팝업 필요 (`AdMob.requestTrackingAuthorization()`).
4. **광고 제거 2,900원**: `cordova-plugin-purchase` 설치 (코드는 이미 들어가 있음, 상품 ID `remove_ads`).
   - 구글 플레이 콘솔: 인앱 상품 → 관리형 상품 `remove_ads`, 가격 ₩2,900
   - 앱스토어 커넥트: 인앱 구입 → 비소모성 `remove_ads`, 가격 ₩2,900 (가격표에서 선택 가능한지 확인)
   - 구매 복원 버튼은 애플 필수 (이미 있음). 결제 위조 막으려면 서버 영수증 검증 추가 권장.
5. **서버 배포**: `server/` 를 Cloud Run, Fly.io, Render 같은 곳에. API 키는 서버 환경변수로만.
   IP당 하루 60회 제한이 들어가 있음.
6. **스토어 심사 대비**
   - 개인정보처리방침 (검색어를 서버로 보내 AI가 처리, KLIPY에 익명 ID와 검색어 전송, 광고 SDK가 광고 ID 수집)
   - 앱 설명에 "KLIPY와 무관한 독립 앱" 표시 (KLIPY 약관), 앱 이름에 KLIPY 넣지 말 것
   - 구글 플레이: 데이터 보안 섹션, 광고 포함 표시, 콘텐츠 등급
   - 개발자 계정: 구글 플레이 1회 $25, 애플 연 $99 (iOS 빌드에 맥 필요)
