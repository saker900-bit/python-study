# 플레이스토어 출시 순서

✅ = 이미 해둔 것, 👉 = 직접 해야 하는 것 (계정·결제·비밀 키라서 대신 못 함)

## 이미 해둔 것
- ✅ 안드로이드 앱 프로젝트 (`jansori/app`, Capacitor). 빌드 확인함 (APK, AAB 둘 다)
- ✅ 앱 아이콘, 시작 화면
- ✅ 광고(AdMob)·결제(RevenueCat)·폰 음성 연결 코드. 지금은 테스트 광고 ID
- ✅ 서버 배포 설정 (`render.yaml`, `jansori/server/Dockerfile`), 하루 사용 횟수 제한, 음성 캐시
- ✅ 개인정보처리방침 페이지 (서버의 `/privacy`)
- ✅ 스토어 설명글, 설문 답, 아이콘·그래픽·스크린샷 (`jansori/store`)

---

## 1단계. 키 2개 받기 (10분)

### 👉 Claude API 키 (사진 비교용)
1. console.anthropic.com 가입
2. Settings → Billing 에서 카드 등록, 크레딧 충전 ($5면 테스트 충분)
3. API Keys → Create Key → `sk-ant-` 로 시작하는 키 복사해서 메모장에 보관

### 👉 ElevenLabs API 키 (목소리용)
1. elevenlabs.io 가입
2. 주소창에 `elevenlabs.io/app/settings/api-keys` → Create API Key → `sk_` 로 시작하는 키 복사
3. 목소리 복제까지 쓰려면 Starter 요금제(월 약 $5) 필요. 캐릭터 기본 목소리만 쓰면 무료로 시작 가능

## 2단계. 캐릭터 목소리 고르기
- Claude에게 "키 준비됨"이라고 하면 입력 창이 뜸 → 키를 넣으면 한국어 목소리 후보를 들어볼 수 있게 만들어 줌
- 직접 고르려면: ElevenLabs → Voice Library → 언어 Korean → 마음에 드는 목소리 "Add to my voices" → 목소리 ID 복사
  (아줌마, 할머니, 아저씨, 아이 4개)

## 3단계. 서버 올리기 (Render, 15분)
1. 👉 render.com 가입 (GitHub 계정으로 로그인)
2. 👉 이 작업 브랜치를 main 에 합치기 (Claude에게 "PR 만들어줘" → GitHub에서 Merge)
3. 👉 Render → New → Blueprint → 저장소 `python-study` 선택 → `render.yaml` 이 자동으로 잡힘
4. 👉 키 입력 칸에 넣기
   - `ANTHROPIC_API_KEY`: 1단계 Claude 키
   - `ELEVENLABS_API_KEY`: 1단계 ElevenLabs 키
   - `ELEVENLABS_VOICE_AJUMMA` / `HALMEONI` / `AJEOSSI` / `KID`: 2단계 목소리 ID
   - `CONTACT_EMAIL`: 문의 받을 이메일 (개인정보처리방침에 나옴)
5. Deploy → 주소가 나옴 (예: `https://jansori-server-abcd.onrender.com`)
6. 브라우저로 `주소/health` → `{"ok":true,...}` 나오면 성공, `주소/privacy` → 개인정보처리방침
- 무료 요금제는 15분 안 쓰면 잠들어서 첫 검사가 1분쯤 걸림. 출시할 땐 Starter($7/월) 추천

## 4단계. 앱에 서버 주소 넣기
- Claude에게 서버 주소를 알려주면 `jansori/app/src/config.js` 에 넣고 다시 빌드해 줌

## 5단계. 플레이 콘솔 가입 (며칠 걸림)
1. 👉 play.google.com/console 가입, 등록비 $25 (한 번만)
2. 👉 신분증 인증. 승인까지 며칠 걸릴 수 있음
3. ⚠️ 개인 계정은 바로 출시가 안 됨: **비공개 테스트에 테스터 12명 이상이 14일 동안 참여**해야 정식 출시 신청 가능
   (가족·친구 구글 계정 12개 미리 모아두기. 규칙은 바뀔 수 있으니 콘솔 안내 확인)

## 6단계. 서명 키 만들고 AAB 만들기 (PC에서, 30분)
1. 👉 Android Studio 설치 (developer.android.com/studio)
2. 👉 Node.js 설치 (nodejs.org, LTS)
3. 저장소를 PC에 받고:
   ```
   cd jansori/app
   npm install
   npm run sync
   npm run open        ← Android Studio 로 열림
   ```
4. 👉 Android Studio 메뉴: **Build → Generate Signed App Bundle or APK → Android App Bundle**
5. 👉 **Create new...** 로 서명 키(keystore) 만들기
   - 저장 위치: 저장소 바깥 (예: `문서/jansori-upload.jks`)
   - 비밀번호, 별명(alias) 꼭 적어두기
   - ⚠️ 이 파일과 비밀번호를 잃어버리면 앱 업데이트가 막힘. 클라우드 드라이브에 백업
6. 👉 release 선택 → Create → `app/release/app-release.aab` 생김
- 다음부터 명령어로 만들려면 `android/keystore.properties` 파일을 만들어 둠 (git 에 안 올라감):
  ```
  storeFile=C:/Users/나/Documents/jansori-upload.jks
  storePassword=비밀번호
  keyAlias=upload
  keyPassword=비밀번호
  ```
  그다음 `cd android && gradlew bundleRelease`

## 7단계. 플레이 콘솔에 앱 만들기
1. 👉 앱 만들기 → 이름 `빠직 잔소리`, 한국어, 앱, 무료
2. 👉 스토어 등록정보: `jansori/store/listing.md` 내용 복사, 이미지는 `jansori/store` 폴더
3. 👉 앱 콘텐츠: listing.md 의 "앱 콘텐츠 설문 답" 대로 체크
4. 👉 테스트 → 비공개 테스트 → 트랙 만들기 → 6단계 AAB 업로드 → 테스터 이메일 추가 → 검토 제출

## 8단계. 광고 제거 상품 (2,900원)
1. 👉 플레이 콘솔 → 설정 → 결제 프로필 만들기 (판매자 계정, 정산받을 계좌)
2. 👉 수익 창출 → 제품 → 인앱 상품 → 만들기
   - 제품 ID: `remove_ads_forever` (정확히 이대로)
   - 이름: 광고 평생 제거 / 가격: 2,900원 → 활성화
   - AAB를 한 번 올린 뒤에야 이 메뉴가 열림
3. 👉 RevenueCat (결제 확인 서비스, 무료로 시작)
   - revenuecat.com 가입 → 프로젝트 만들기 → Google Play 앱 추가 (패키지 `com.bbajik.jansori`)
   - 화면 안내대로 "서비스 계정 키(JSON)" 연결 (RevenueCat 문서에 그림으로 나옴)
   - Products 에서 `remove_ads_forever` 가져오기
   - Entitlements → `no_ads` 만들고 그 상품 연결
   - API keys → Google Play 공개 키 (`goog_` 로 시작) 복사 → Claude에게 알려주기 (공개 키라 채팅에 줘도 됨)

## 9단계. 진짜 광고 (AdMob)
1. 👉 admob.google.com 가입 → 앱 추가 → Android → 앱 이름
2. 👉 앱 ID (`ca-app-pub-숫자~숫자`) 와 전면 광고 단위 ID (`ca-app-pub-숫자/숫자`) 받기
3. Claude에게 두 ID 알려주면 앱에 넣고 테스트 광고를 끔
- ⚠️ 진짜 광고를 본인이 계속 누르면 계정 정지됨. 테스트는 테스트 광고로

## 10단계. 출시
1. 비공개 테스트 14일 끝나면 → 프로덕션 → 출시 신청
2. 심사는 보통 며칠 걸림
