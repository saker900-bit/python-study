# 원터치 클리너 (OneTouch Cleaner)

버튼 한 번으로 선택한 앱을 강제 종료하고 캐시를 지우는 안드로이드 앱.

- 적용/제외 앱 선택 (일반 앱 기본 적용, 시스템 앱 기본 제외)
- 무료: 보상형 광고 1회 시청 후 실행 / 유료: 광고 평생 제거 ₩5,900 (`remove_ads_lifetime`)
- Kotlin + Jetpack Compose, minSdk 26 / targetSdk 35

## 동작 원리
안드로이드는 일반 앱이 다른 앱을 종료하거나 캐시를 지우는 API를 막아두었습니다
(`killBackgroundProcesses` 는 Android 14부터 자기 앱만 가능, `CLEAR_APP_CACHE` 는 시스템 전용).
그래서 접근성 서비스(`CleanerService`)가 각 앱의 **앱 정보 화면**을 열고
`강제 종료 → 확인`, `저장공간 → 캐시 지우기` 버튼을 사용자 대신 누릅니다.
진행 중에는 화면을 덮는 진행 표시창과 '중지' 버튼이 뜹니다.

## 파일 구성
| 파일 | 역할 |
|---|---|
| `CleanerService.kt` | 정리 엔진 (접근성 자동화, 제조사·언어별 버튼 이름) |
| `MainActivity.kt` | 화면 (앱 목록, 정리 시작, 권한 고지, 결과) |
| `AdsManager.kt` | AdMob 보상형 광고 + 동의(UMP) |
| `BillingManager.kt` | Play 결제: 광고 제거 구매/복원 |
| `AppRepository.kt`, `Prefs.kt` | 앱 목록, 적용/제외 저장 |

## 빌드
GitHub Actions(`.github/workflows/android.yml`)가 push 마다 디버그 APK를 만듭니다.
업로드 키 Secrets 를 등록하면 Play 업로드용 AAB 도 만듭니다.
로컬: `./gradlew assembleDebug` (Android SDK 필요)

출시 절차는 [`docs/LAUNCH_GUIDE.md`](docs/LAUNCH_GUIDE.md) 참고.
