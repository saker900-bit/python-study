import { Link, router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Linking, Pressable, RefreshControl, SectionList, Text, View } from "react-native";
import { LineBadge } from "../components/LineBadge";
import { api, type Incident } from "../lib/api";
import { useApp } from "../lib/AppContext";
import { lineById } from "../lib/lines";

function ago(iso: string) {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 1) return "방금";
  if (m < 60) return `${m}분 전`;
  return `${Math.floor(m / 60)}시간 전`;
}

function Card({ it }: { it: Incident }) {
  const active = it.status === "active";
  const where = [lineById(it.line)?.name, it.station && `${it.station}역`].filter(Boolean).join(" ");
  return (
    <Pressable
      onPress={() => it.sources[0] && Linking.openURL(it.sources[0].url)}
      style={{
        backgroundColor: "#fff",
        marginHorizontal: 16,
        marginVertical: 6,
        padding: 14,
        borderRadius: 14,
        borderLeftWidth: 5,
        borderLeftColor: active ? "#E53935" : "#43A047",
        opacity: active ? 1 : 0.75,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <LineBadge line={it.line} />
        <Text style={{ fontSize: 16, fontWeight: "700", flex: 1 }}>{where || "노선 확인 중"}</Text>
        <Text style={{ color: "#888", fontSize: 12 }}>{ago(it.first_seen)}</Text>
      </View>
      <Text style={{ marginTop: 8, fontSize: 15, fontWeight: "600", color: active ? "#C62828" : "#2E7D32" }}>
        {active ? `🚨 ${it.cause}(으)로 지연` : `✅ 정상 운행 재개 (${it.cause})`}
      </Text>
      <Text style={{ marginTop: 4, color: "#555" }} numberOfLines={2}>
        {it.summary}
      </Text>
      <Text style={{ marginTop: 6, color: "#999", fontSize: 12 }}>
        출처 {it.sources.length}건 · {[...new Set(it.sources.map((s) => s.kind))].join(", ")}
      </Text>
    </Pressable>
  );
}

export default function Feed() {
  const { sub } = useApp();
  const [items, setItems] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await api.incidents(24));
      setError(null);
    } catch {
      setError("서버에 연결하지 못했어요.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  const active = items.filter((i) => i.status === "active");
  const resolved = items.filter((i) => i.status === "resolved");

  return (
    <View style={{ flex: 1, backgroundColor: "#F2F3F5" }}>
      {!sub?.active && (
        <Pressable
          onPress={() => router.push("/paywall")}
          style={{ backgroundColor: "#1E2A78", padding: 14, margin: 16, marginBottom: 4, borderRadius: 14 }}
        >
          <Text style={{ color: "#fff", fontWeight: "800", fontSize: 15 }}>🔔 지연 즉시 푸시 받기</Text>
          <Text style={{ color: "#C9D0FF", marginTop: 2 }}>첫 달 무료 · 이후 월 2,900원</Text>
        </Pressable>
      )}
      <SectionList
        sections={[
          { title: `지연 중 (${active.length})`, data: active },
          { title: "최근 복구됨", data: resolved },
        ]}
        keyExtractor={(i) => i.id}
        renderItem={({ item }) => <Card it={item} />}
        renderSectionHeader={({ section }) => (
          <Text style={{ marginHorizontal: 16, marginTop: 16, marginBottom: 4, fontWeight: "800", color: "#333" }}>
            {section.title}
          </Text>
        )}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
        ListFooterComponent={
          <View style={{ padding: 24, alignItems: "center", gap: 12 }}>
            {error && <Text style={{ color: "#C62828" }}>{error}</Text>}
            {!error && active.length === 0 && <Text style={{ color: "#666" }}>지금은 보고된 지연이 없어요 🙌</Text>}
            <Link href="/settings" style={{ color: "#1E2A78", fontWeight: "700" }}>
              알림 설정 →
            </Link>
          </View>
        }
        stickySectionHeadersEnabled={false}
      />
    </View>
  );
}
