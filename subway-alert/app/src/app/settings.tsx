import { router } from "expo-router";
import { Alert, Linking, Pressable, ScrollView, Switch, Text, View } from "react-native";
import { LineBadge } from "../components/LineBadge";
import { useApp } from "../lib/AppContext";
import { PRIVACY_URL, TERMS_URL } from "../lib/config";
import { LINES } from "../lib/lines";
import { getSubState, manageSubscription, restore } from "../lib/purchases";

const Row = ({ children }: { children: React.ReactNode }) => (
  <View style={{ backgroundColor: "#fff", padding: 16, borderRadius: 14, marginHorizontal: 16, marginTop: 12 }}>{children}</View>
);

export default function Settings() {
  const { sub, setSub, settings, updateSettings, pushToken, refreshPush } = useApp();
  const all = settings.lines.length === 0;

  const toggleLine = (id: string) => {
    const set = new Set(settings.lines);
    set.has(id) ? set.delete(id) : set.add(id);
    updateSettings({ lines: [...set] });
  };

  return (
    <ScrollView style={{ backgroundColor: "#F2F3F5" }} contentContainerStyle={{ paddingBottom: 40 }}>
      <Row>
        <Text style={{ fontWeight: "800", fontSize: 16 }}>구독</Text>
        {sub?.active ? (
          <Text style={{ marginTop: 6, color: "#333" }}>
            {sub.inTrial ? "무료체험 중" : "이용 중"}
            {sub.expiresAt ? ` · ${sub.willRenew ? "다음 결제일" : "만료일"} ${sub.expiresAt.toLocaleDateString("ko-KR")}` : ""}
          </Text>
        ) : (
          <Pressable onPress={() => router.push("/paywall")}>
            <Text style={{ marginTop: 6, color: "#1E2A78", fontWeight: "700" }}>구독하고 푸시 알림 받기 →</Text>
          </Pressable>
        )}
        <View style={{ flexDirection: "row", gap: 20, marginTop: 12 }}>
          {sub?.active && (
            <Text
              style={{ color: "#1E2A78" }}
              onPress={async () => {
                await manageSubscription();
                setSub(await getSubState());
              }}
            >
              구독 관리/해지
            </Text>
          )}
          <Text
            style={{ color: "#1E2A78" }}
            onPress={async () => {
              const s = await restore();
              setSub(s);
              Alert.alert(s.active ? "구독이 복원됐어요" : "복원할 구독이 없어요");
            }}
          >
            구매 복원
          </Text>
        </View>
      </Row>

      <Row>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <Text style={{ fontWeight: "800", fontSize: 16 }}>지연 알림 받기</Text>
          <Switch value={settings.enabled} onValueChange={(v) => updateSettings({ enabled: v })} />
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 12 }}>
          <Text style={{ fontSize: 15 }}>정상 운행 재개 알림</Text>
          <Switch value={settings.notifyResolved} onValueChange={(v) => updateSettings({ notifyResolved: v })} />
        </View>
        {sub?.active && !pushToken && (
          <Pressable onPress={refreshPush}>
            <Text style={{ color: "#C62828", marginTop: 12 }}>
              알림 권한이 꺼져 있어요. 눌러서 다시 시도하거나 휴대폰 설정에서 허용해 주세요.
            </Text>
          </Pressable>
        )}
      </Row>

      <Row>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <Text style={{ fontWeight: "800", fontSize: 16 }}>알림 받을 노선</Text>
          <Text style={{ color: "#1E2A78" }} onPress={() => updateSettings({ lines: [] })}>
            {all ? "전체 노선 ✓" : "전체 선택"}
          </Text>
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
          {LINES.map((l) => {
            const on = all || settings.lines.includes(l.id);
            return (
              <Pressable
                key={l.id}
                onPress={() => toggleLine(l.id)}
                style={{
                  flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: 6, paddingHorizontal: 10,
                  borderRadius: 20, borderWidth: 1.5, borderColor: on ? l.color : "#ddd", opacity: on ? 1 : 0.5,
                }}
              >
                <LineBadge line={l.id} size="sm" />
                <Text style={{ fontWeight: "600" }}>{l.name}</Text>
              </Pressable>
            );
          })}
        </View>
      </Row>

      <View style={{ flexDirection: "row", justifyContent: "center", gap: 20, marginTop: 24 }}>
        <Text style={{ color: "#666" }} onPress={() => Linking.openURL(TERMS_URL)}>이용약관</Text>
        <Text style={{ color: "#666" }} onPress={() => Linking.openURL(PRIVACY_URL)}>개인정보처리방침</Text>
      </View>
    </ScrollView>
  );
}
