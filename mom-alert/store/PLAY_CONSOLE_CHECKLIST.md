# Play Console 출시 체크리스트

## 1. 서명 키 만들기 (한 번만, 절대 잃어버리면 안 됨)
```bash
keytool -genkeypair -v -keystore release.jks -alias momradar \
  -keyalg RSA -keysize 2048 -validity 10000
```
- `release.jks` 와 비밀번호는 안전한 곳에 백업. **레포에 커밋 금지.**

## 2. GitHub에서 자동으로 .aab 빌드하기
레포 Settings → Secrets and variables → Actions 에 등록:
| 이름 | 값 |
|---|---|
| `KEYSTORE_BASE64` | `base64 -w0 release.jks` 결과 |
| `KEYSTORE_PASSWORD` | 키스토어 비밀번호 |
| `KEY_ALIAS` | `momradar` |
| `KEY_PASSWORD` | 키 비밀번호 |

그 뒤 Actions에서 빌드하면 `mom-radar-release-aab` 가 생김 → Play Console에 업로드.

## 3. Play Console에서 해야 할 것
- [ ] 개발자 계정 (등록비 $25)
- [ ] 개인정보처리방침 URL: `store/PRIVACY_POLICY.md` 를 공개 웹페이지로 올리기
      (레포를 public으로 하거나 GitHub Pages / 노션 등)
- [ ] **포그라운드 서비스 권한 선언**: 유형 `microphone`
      - 설명 예: "사용자가 직접 감시를 시작하면, 앱이 백그라운드에 있어도 주변 발소리 크기를 측정해 알림을 보냅니다. 감지 중에는 항상 알림이 표시되며 사용자가 언제든 끌 수 있습니다."
      - 동영상 링크 요구 시: 앱에서 감시 시작 → 홈으로 나감 → 걸어와서 알림 오는 장면 녹화 (유튜브 일부공개)
- [ ] 데이터 보안: "수집하는 데이터 없음", "공유하는 데이터 없음"
- [ ] 콘텐츠 등급 설문
- [ ] 스크린샷 2장 이상 (폰), 아이콘 512x512, 그래픽 이미지 1024x500
- [ ] 신규 개인 개발자 계정이면 **비공개 테스트 12명 이상 × 14일** 후에 프로덕션 출시 가능

## 4. 버전 올리기
`app/build.gradle.kts` 의 `versionCode` 를 매번 +1, `versionName` 도 변경.
