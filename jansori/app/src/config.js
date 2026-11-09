// 앱 설정. 스토어에 올리기 전에 이 파일만 고치면 돼요.
window.JANSORI_CONFIG = {
  // 1) 배포한 서버 주소 (Render 등). 끝에 / 없이.
  api: "https://YOUR-SERVER.onrender.com",

  // 2) AdMob 전면 광고 단위 ID. 아래는 구글이 주는 '테스트 광고' ID라 그대로 두면 테스트 광고가 나옴.
  //    진짜 ID로 바꿀 때 adTesting 도 false 로.
  admobInterstitialId: "ca-app-pub-3940256099942544/1033173712",
  adTesting: true,

  // 3) RevenueCat 안드로이드 공개 API 키 (goog_ 로 시작). 비워두면 결제 버튼이 테스트 결제로 동작.
  revenuecatKey: "",
  // RevenueCat 에서 만든 권한(Entitlement) 이름
  entitlement: "no_ads",
};
