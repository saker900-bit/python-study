import { router } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useApp } from "../lib/AppContext";
import { PRICE, PRIVACY_URL, TERMS_URL } from "../lib/config";
import { scheduleTrialEndReminder } from "../lib/notifications";
import { buy, getPlans, isUserCancelled, MOCK, restore, type Plan } from "../lib/purchases";

const FEATURES = [
  "🚨 전 노선·전 역 지연 발생 즉시 푸시",
  "🔎 뉴스·SNS·공식 공지를 24시간 실시간 감시",
  "📍 어느 역, 무슨 이유인지 한 줄로 (환자 발생, 고장, 화재…)",
  "✅ 정상 운행 재개되면 복구 알림까지",
  "🎯 내가 타는 노선만 골라 받기",
];

export default function Paywall() {
  const { setSub, refreshPush } = useApp();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selected, setSelected] = useState<Plan["id"]>("yearly");
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getPlans().then(setPlans).catch(() => Alert.alert("상품 정보를 불러오지 못했어요"));
  }, []);

  const plan = plans.find((p) => p.id === selected);

  async function onBuy() {
    if (!plan) return;
    if (!agreed) {
      Alert.alert("동의가 필요해요", "무료체험 종료 후 자동 정기결제에 동의해 주세요.");
      return;
    }
    setBusy(true);
    try {
      const s = await buy(plan);
      setSub(s);
      if (s.active) {
        await refreshPush();
        if (s.inTrial && s.expiresAt) await scheduleTrialEndReminder(s.expiresAt, plan.priceText);
        router.back();
      }
    } catch (e) {
      if (!isUserCancelled(e)) Alert.alert("결제 실패", e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onRestore() {
    setBusy(true);
    try {
      const s = await restore();
      setSub(s);
      Alert.alert(s.active ? "구독이 복원됐어요" : "복원할 구독이 없어요");
      if (s.active) router.back();
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#0F1640" }}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingBottom: 40 }}>
        <Pressable onPress={() => router.back()} hitSlop={16} style={{ alignSelf: "flex-end" }}>
          <Text style={{ color: "#8C95C9", fontSize: 22 }}>✕</Text>
        </Pressable>
        <Text style={{ color: "#fff", fontSize: 28, fontWeight: "900", marginTop: 8 }}>
          지하철 지연,{"\n"}뉴스보다 먼저 알려드려요
        </Text>
        <View style={{ marginTop: 20, gap: 10 }}>
          {FEATURES.map((f) => (
            <Text key={f} style={{ color: "#DDE2FF", fontSize: 15 }}>
              {f}
            </Text>
          ))}
        </View>

        <View style={{ marginTop: 28, gap: 12 }}>
          {plans.map((p) => {
            const on = p.id === selected;
            return (
              <Pressable
                key={p.id}
                onPress={() => setSelected(p.id)}
                style={{
                  borderWidth: 2,
                  borderColor: on ? "#FFD54F" : "#2E3A7A",
                  backgroundColor: on ? "#1E2A78" : "#151E55",
                  borderRadius: 16,
                  padding: 16,
                }}
              >
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Text style={{ color: "#fff", fontSize: 17, fontWeight: "800" }}>{p.title}</Text>
                  {p.id === "yearly" && (
                    <Text style={{ backgroundColor: "#FFD54F", color: "#000", fontWeight: "900", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8, overflow: "hidden" }}>
                      30% 할인
                    </Text>
                  )}
                </View>
                <Text style={{ color: "#fff", fontSize: 20, fontWeight: "900", marginTop: 6 }}>{p.priceText}</Text>
                <Text style={{ color: "#AAB3E6", marginTop: 2 }}>{p.subText}</Text>
                {p.trialText && <Text style={{ color: "#FFD54F", marginTop: 6, fontWeight: "700" }}>{p.trialText}</Text>}
              </Pressable>
            );
          })}
          {!plans.length && <ActivityIndicator color="#fff" />}
        </View>

        <Pressable onPress={() => setAgreed(!agreed)} style={{ flexDirection: "row", gap: 10, marginTop: 20, alignItems: "flex-start" }}>
          <View
            style={{
              width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: "#FFD54F",
              backgroundColor: agreed ? "#FFD54F" : "transparent", alignItems: "center", justifyContent: "center",
            }}
          >
            {agreed && <Text style={{ fontWeight: "900" }}>✓</Text>}
          </View>
          <Text style={{ color: "#DDE2FF", flex: 1, lineHeight: 20 }}>
            (필수) {PRICE.trialDays}일 무료체험이 끝나면 선택한 요금({plan?.priceText ?? "-"})이 스토어에 등록된
            결제수단으로 자동 결제되며, 해지 전까지 매 {selected === "yearly" ? "년" : "월"} 자동 갱신되는 것에 동의합니다.
          </Text>
        </Pressable>

        <Pressable
          disabled={busy || !plan}
          onPress={onBuy}
          style={{ marginTop: 20, backgroundColor: agreed ? "#FFD54F" : "#6B6440", padding: 18, borderRadius: 16, alignItems: "center" }}
        >
          {busy ? <ActivityIndicator /> : <Text style={{ fontSize: 18, fontWeight: "900" }}>첫 달 무료로 시작하기</Text>}
        </Pressable>

        <Text style={{ color: "#8C95C9", fontSize: 12, marginTop: 16, lineHeight: 18 }}>
          • 무료체험을 시작하려면 App Store / Google Play 계정에 결제수단이 등록되어 있어야 합니다.{"\n"}
          • 체험 종료 3일 전에 알림으로 안내해 드립니다. 체험 기간 중 해지하면 요금이 청구되지 않습니다.{"\n"}
          • 구독은 기간 종료 24시간 전까지 해지하지 않으면 자동 갱신됩니다. 해지는 스토어의 구독 관리에서 할 수 있습니다.{"\n"}
          • 무료체험은 계정당 1회만 제공됩니다.
          {MOCK ? "\n• [개발 모드] 실제 결제가 일어나지 않습니다." : ""}
        </Text>

        <View style={{ flexDirection: "row", justifyContent: "center", gap: 20, marginTop: 16 }}>
          <Text style={{ color: "#AAB3E6" }} onPress={onRestore}>구매 복원</Text>
          <Text style={{ color: "#AAB3E6" }} onPress={() => Linking.openURL(TERMS_URL)}>이용약관</Text>
          <Text style={{ color: "#AAB3E6" }} onPress={() => Linking.openURL(PRIVACY_URL)}>개인정보처리방침</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
