// 안드로이드 앱에서만 동작: 서버 주소, 광고(AdMob), 결제(RevenueCat), 폰 음성(TTS)을 웹 화면에 연결
(function () {
  const cap = window.Capacitor;
  if (!cap || !cap.isNativePlatform || !cap.isNativePlatform()) return;
  const P = cap.Plugins || {};
  const C = window.JANSORI_CONFIG || {};

  if (C.api && !/YOUR-SERVER/.test(C.api)) window.JANSORI_API = C.api;

  // 광고
  if (P.AdMob && C.admobInterstitialId) {
    P.AdMob.initialize({ initializeForTesting: !!C.adTesting }).catch((e) => console.warn("admob init", e));
    window.JANSORI_ADMOB_ID = C.admobInterstitialId;
    window.JANSORI_ADMOB_TESTING = !!C.adTesting;
  }

  // 결제 (광고 평생 제거, 비소모성 상품)
  if (P.Purchases && C.revenuecatKey) {
    const ready = P.Purchases.configure({ apiKey: C.revenuecatKey }).catch((e) => console.warn("purchases init", e));
    const has = (info) => !!(info && info.entitlements && info.entitlements.active && info.entitlements.active[C.entitlement || "no_ads"]);
    window.JANSORI_STORE = {
      async buy(productId) {
        await ready;
        const { products } = await P.Purchases.getProducts({ productIdentifiers: [productId], type: "NON_SUBSCRIPTION" });
        if (!products || !products.length) throw new Error("상품을 못 찾음: " + productId);
        try {
          const r = await P.Purchases.purchaseStoreProduct({ product: products[0] });
          return has(r.customerInfo);
        } catch (e) {
          if (e && e.userCancelled) return false;
          throw e;
        }
      },
      async restore() { await ready; const r = await P.Purchases.restorePurchases(); return has(r.customerInfo); },
      async check() { await ready; const r = await P.Purchases.getCustomerInfo(); return has(r.customerInfo); },
    };
  }

  // 폰 기본 음성: 안드로이드 WebView 에는 브라우저 음성 기능이 없어서 플러그인으로
  if (P.TextToSpeech) {
    window.JANSORI_NATIVE_TTS = (text, pitch, rate) =>
      P.TextToSpeech.speak({ text, lang: "ko-KR", pitch, rate: Math.min(1.6, rate), volume: 1, category: "playback" });
    window.JANSORI_NATIVE_TTS_STOP = () => P.TextToSpeech.stop().catch(() => {});
  }
})();
