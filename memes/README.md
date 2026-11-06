# 밈 탐정

기억나는 대로 밈을 설명하면 짤을 화면 가운데에 크게 띄우고 "이거 맞음?" 하고 물어보는 앱.
아니면 다음 후보, 맞으면 이름·출처·설명과 짤 저장 버튼.

## 지금 되는 것

- 밈 도감 77개 (한국 32, 해외 45). 짤은 Tenor에서 골라 사람이 눈으로 확인한 것만.
- 검색: Claude가 도감에서 후보를 골라 줌 (Claude 앱 안 = 아티팩트 기능, 스토어 앱 = 내 서버).
  둘 다 없으면 단어 비교로 대충 찾음.
- 검색 후 결과 보기 전에 광고 (스토어 앱 = AdMob 전면 광고, 그 외 = "광고 자리" 미리보기 3초)
- 짤 저장 (mp4). 스토어 앱에서는 공유 창이 열려서 갤러리 저장, 카톡 전송 가능.
- 광고 평생 제거 2,900원 1회 결제 + 구매 복원
- 매일 새벽 자동으로 새 밈 추가 (Claude 예약 작업, 절차는 `DAILY_UPDATE.md`)

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

## 출시 전에 꼭 해결할 것: 짤 저작권

**지금 상태 그대로 스토어에 내면 거절되거나 신고당할 수 있다.**

- 도감 짤 대부분이 영화·드라마·예능 장면이다 (타짜, 베테랑, 무한도전 등). 저작권은 방송사·제작사에 있다.
- 광고 수익과 유료 결제가 붙은 앱에서 남의 영상을 쓰면 애플 심사 지침 5.2(지식재산권),
  구글 플레이 지식재산권 정책에 걸린다. 권리자 신고가 들어오면 앱이 내려간다.
- Tenor 웹페이지에서 짤 주소를 긁어 오는 지금 방식은 Tenor 이용약관 위반이다
  (공식 API + API 키 + "Powered by Tenor" 표시가 원칙).

해결 방법 (추천 순):

1. **GIPHY 공식 API로 바꾸기**: 상업 앱에서 쓸 수 있게 열려 있고 표시 규칙만 지키면 됨
   (developers.giphy.com 에서 키 발급, 프로덕션 키 신청, "Powered by GIPHY" 표시).
   도감에는 밈 이름/검색어만 두고 짤은 API로 그때그때 받아 오는 구조. 한국 밈 짤은 GIPHY에 적은 편이라 커버리지가 줄어듦.
2. **Tenor 공식 API** (Google Cloud에서 키 발급). 한국 짤이 GIPHY보다 많음. 출시 전에 API 정책과 서비스 지속 여부 확인.
3. 직접 만든 짤만 쓰기 (밈을 따라 그린 일러스트, 직접 찍은 패러디).

어느 쪽이든 앱 안에 "짤 저작권은 각 권리자에게 있음, 신고 연락처" 안내와 신고 기능을 넣는다.

## PC에서 Claude Code로 할 일 (스토어까지)

1. **앱으로 감싸기**: Capacitor로 `site/` 를 안드로이드/iOS 앱으로
   (`npm i @capacitor/core @capacitor/cli`, `npx cap init`, `npx cap add android`, `npx cap add ios`).
   저장 기능용 `@capacitor/filesystem`, `@capacitor/share` 설치.
2. **광고 (AdMob)**: `@capacitor-community/admob` 설치. AdMob 가입 → 앱 등록 → 전면 광고 단위 2개 (안드로이드/iOS) 만들기.
   `web/template.html` 의 `ADMOB` 에 내 광고 단위 ID 넣고 `testing: false`.
   iOS는 앱 추적 동의(ATT) 팝업 필요 (`AdMob.requestTrackingAuthorization()`).
3. **광고 제거 2,900원**: `cordova-plugin-purchase` 설치 (코드는 이미 들어가 있음, 상품 ID `remove_ads`).
   - 구글 플레이 콘솔: 인앱 상품 → 관리형 상품 `remove_ads`, 가격 ₩2,900
   - 앱스토어 커넥트: 인앱 구입 → 비소모성 `remove_ads`, 가격 ₩2,900 (가격표에서 선택 가능한지 확인)
   - 구매 복원 버튼은 애플 필수 (이미 있음). 결제 위조 막으려면 서버 영수증 검증 추가 권장.
4. **서버 배포**: `server/` 를 Cloud Run, Fly.io, Render 같은 곳에. API 키는 서버 환경변수로만.
   IP당 하루 60회 제한이 들어가 있음.
5. **스토어 심사 대비**
   - 개인정보처리방침 (검색어를 서버로 보내 AI가 처리, 광고 SDK가 광고 ID 수집)
   - 구글 플레이: 데이터 보안 섹션, 광고 포함 표시, 콘텐츠 등급
   - 개발자 계정: 구글 플레이 1회 $25, 애플 연 $99 (iOS 빌드에 맥 필요)
