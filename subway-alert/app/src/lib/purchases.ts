import Purchases, {
  type CustomerInfo,
  type PurchasesPackage,
  LOG_LEVEL,
} from "react-native-purchases";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { ENTITLEMENT_ID, PRICE, REVENUECAT_KEY, won } from "./config";

/**
 * 결제는 App Store / Google Play 인앱 정기구독을 RevenueCat 으로 관리한다.
 * - 결제수단 등록, 무료체험(첫 달), 자동갱신 동의 화면은 스토어 결제 시트가 처리
 * - RevenueCat 키가 없으면(개발용) 가짜 결제로 동작
 */
export const MOCK = !REVENUECAT_KEY;

export type Plan = {
  id: "monthly" | "yearly";
  title: string;
  priceText: string;
  subText: string;
  trialText: string | null;
  pkg: PurchasesPackage | null;
};

export type SubState = {
  active: boolean;
  inTrial: boolean;
  expiresAt: Date | null;
  willRenew: boolean;
  appUserId: string;
};

let configured = false;

export async function initPurchases(): Promise<string> {
  if (MOCK) {
    let id = await AsyncStorage.getItem("mock.uid");
    if (!id) {
      id = `mock_${Math.random().toString(36).slice(2, 12)}`;
      await AsyncStorage.setItem("mock.uid", id);
    }
    return id;
  }
  if (!configured) {
    if (__DEV__) Purchases.setLogLevel(LOG_LEVEL.DEBUG);
    Purchases.configure({ apiKey: REVENUECAT_KEY! });
    configured = true;
  }
  return Purchases.getAppUserID();
}

function toState(info: CustomerInfo): SubState {
  const ent = info.entitlements.active[ENTITLEMENT_ID];
  return {
    active: !!ent,
    inTrial: ent?.periodType === "TRIAL",
    expiresAt: ent?.expirationDate ? new Date(ent.expirationDate) : null,
    willRenew: ent?.willRenew ?? false,
    appUserId: info.originalAppUserId,
  };
}

export async function getSubState(): Promise<SubState> {
  if (MOCK) {
    const raw = await AsyncStorage.getItem("mock.sub");
    const uid = (await AsyncStorage.getItem("mock.uid")) ?? "mock";
    if (!raw) return { active: false, inTrial: false, expiresAt: null, willRenew: false, appUserId: uid };
    const s = JSON.parse(raw);
    return { ...s, expiresAt: s.expiresAt ? new Date(s.expiresAt) : null, appUserId: uid };
  }
  return toState(await Purchases.getCustomerInfo());
}

export function onSubChange(cb: (s: SubState) => void) {
  if (MOCK) return () => {};
  const listener = (info: CustomerInfo) => cb(toState(info));
  Purchases.addCustomerInfoUpdateListener(listener);
  return () => Purchases.removeCustomerInfoUpdateListener(listener);
}

const FALLBACK: Plan[] = [
  {
    id: "yearly",
    title: "연간 구독",
    priceText: `${won(PRICE.yearly)}/년`,
    subText: `월 ${won(Math.round(PRICE.yearly / 12))}꼴 · ${won(PRICE.yearlyFull)}에서 30% 할인`,
    trialText: "첫 달 무료",
    pkg: null,
  },
  {
    id: "monthly",
    title: "월간 구독",
    priceText: `${won(PRICE.monthly)}/월`,
    subText: "언제든 해지 가능",
    trialText: "첫 달 무료",
    pkg: null,
  },
];

export async function getPlans(): Promise<Plan[]> {
  if (MOCK) return FALLBACK;
  const offerings = await Purchases.getOfferings();
  const cur = offerings.current;
  if (!cur) return FALLBACK;
  const plans: Plan[] = [];
  if (cur.annual) {
    const p = cur.annual.product;
    plans.push({
      ...FALLBACK[0],
      priceText: `${p.priceString}/년`,
      subText: `월 ${p.pricePerMonthString ?? ""}꼴 · 30% 할인`,
      trialText: p.introPrice?.price === 0 ? "첫 달 무료" : null,
      pkg: cur.annual,
    });
  }
  if (cur.monthly) {
    const p = cur.monthly.product;
    plans.push({
      ...FALLBACK[1],
      priceText: `${p.priceString}/월`,
      trialText: p.introPrice?.price === 0 ? "첫 달 무료" : null,
      pkg: cur.monthly,
    });
  }
  return plans.length ? plans : FALLBACK;
}

export async function buy(plan: Plan): Promise<SubState> {
  if (MOCK) {
    const trialEnd = new Date(Date.now() + PRICE.trialDays * 86400000);
    const s = { active: true, inTrial: true, expiresAt: trialEnd.toISOString(), willRenew: true };
    await AsyncStorage.setItem("mock.sub", JSON.stringify(s));
    return getSubState();
  }
  if (!plan.pkg) throw new Error("상품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.");
  const { customerInfo } = await Purchases.purchasePackage(plan.pkg);
  return toState(customerInfo);
}

export async function restore(): Promise<SubState> {
  if (MOCK) return getSubState();
  return toState(await Purchases.restorePurchases());
}

export async function manageSubscription() {
  if (MOCK) {
    await AsyncStorage.removeItem("mock.sub");
    return;
  }
  await Purchases.showManageSubscriptions();
}

export const isUserCancelled = (e: unknown) =>
  typeof e === "object" && e !== null && (e as { userCancelled?: boolean }).userCancelled === true;
