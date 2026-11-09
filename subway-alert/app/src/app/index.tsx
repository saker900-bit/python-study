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

const KIND_LABEL: Record<string, string> = { news: "뉴스", x: "X", instagram: "인스타", official: "공식" };
const KIND_STYLE: Record<string, { bg: string; fg: string }> = {
  news: { bg: "#E8EBFA", fg: "#1E2A78" },
  official: { bg: "#E3F5EA", fg: "#1F9D55" },
  x: { bg: "#ECEDF1", fg: "#141A33" },
  instagram: { bg: "#FCE8F0", fg: "#B4235B" },
};

function SourceRow({ s }: { s: Incident["sources"][number] }) {
  const st = KIND_STYLE[s.kind] ?? KIND_STYLE.x;
  return (
    <Pressable
      onPress={() => Linking.openURL(s.url)}
      accessibilityRole="link"
      accessibilityLabel={`${KIND_LABEL[s.kind] ?? s.kind} 원문 보기: ${s.title}`}
      style={({ pressed }) => ({
        flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 8, paddingHorizontal: 10,
        borderRadius: 10, backgroundColor: pressed ? "#E3E6EE" : "#F4F5F8",
      })}
    >
      <Text style={{ backgroundColor: st.bg, color: st.fg, fontWeight: "700", fontSize: 11, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: "hidden" }}>
        {KIND_LABEL[s.kind] ?? s.kind}
      </Text>
      <Text style={{ flex: 1, color: "#333", fontSize: 13 }} numberOfLines={1}>{s.title}</Text>
      <Text style={{ color: "#1E2A78", fontWeight: "700" }}>›</Text>
    </Pressable>
  );
}

function Card({ it }: { it: Incident }) {
  const [open, setOpen] = useState(false);
  const active = it.status === "active";
  const where = [lineById(it.line)?.name, it.station && `${it.station}역`].filter(Boolean).join(" ");
  // 뉴스·공식 출처를 먼저 보여준다
  const order = ["official", "news", "x", "instagram"];
  const sources = [...it.sources].sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind));
  const shown = open ? sources : sources.slice(0, 2);
  return (
    <View
      style={{
        backgroundColor: "#fff",
        marginHorizontal: 16,
        marginVertical: 6,
        padding: 14,
        borderRadius: 14,
        borderLeftWidth: 5,
        borderLeftColor: active ? "#E53935" : "#43A047",
        opacity: active ? 1 : 0.8,
      }}
    >
      <Pressable onPress={() => sources[0] && Linking.openURL(sources[0].url)}>
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
      </Pressable>
      <View style={{ marginTop: 10, gap: 6 }}>
        {shown.map((s) => <SourceRow key={s.url} s={s} />)}
        {sources.length > 2 && (
          <Text onPress={() => setOpen(!open)} style={{ color: "#1E2A78", fontWeight: "700", fontSize: 13, paddingVertical: 4 }}>
            {open ? "접기" : `출처 ${sources.length - 2}건 더 보기`}
          </Text>
        )}
      </View>
    </View>
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
