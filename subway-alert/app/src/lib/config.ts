import { Platform } from "react-native";

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export const REVENUECAT_KEY =
  Platform.OS === "ios"
    ? process.env.EXPO_PUBLIC_RC_IOS_KEY
    : process.env.EXPO_PUBLIC_RC_ANDROID_KEY;

// RevenueCat 대시보드의 Entitlement 식별자
export const ENTITLEMENT_ID = "premium";

// 스토어 가격을 못 불러왔을 때 보여줄 기본값 (실제 청구 금액은 스토어 설정을 따름)
export const PRICE = {
  monthly: 2900,
  yearlyFull: 2900 * 12, // 34,800
  yearly: Math.round(2900 * 12 * 0.7), // 24,360 (30% 할인)
  trialDays: 30,
};

export const won = (n: number) => `${n.toLocaleString("ko-KR")}원`;

// 스토어 심사에 필수: 이용약관 / 개인정보처리방침 URL (배포 전에 실제 주소로 교체)
export const TERMS_URL = process.env.EXPO_PUBLIC_TERMS_URL ?? "https://example.com/terms";
export const PRIVACY_URL = process.env.EXPO_PUBLIC_PRIVACY_URL ?? "https://example.com/privacy";
