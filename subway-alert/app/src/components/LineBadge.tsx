import { Text, View } from "react-native";
import { lineById } from "../lib/lines";

export function LineBadge({ line, size = "md" }: { line: string | null; size?: "sm" | "md" }) {
  const l = lineById(line);
  const label = l ? l.name.replace("호선", "") : "?";
  const short = label.length <= 2;
  const h = size === "sm" ? 22 : 30;
  return (
    <View
      style={{
        backgroundColor: l?.color ?? "#888",
        height: h,
        minWidth: h,
        borderRadius: h / 2,
        paddingHorizontal: short ? 0 : 8,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Text style={{ color: "#fff", fontWeight: "800", fontSize: size === "sm" ? 11 : 13 }}>{label}</Text>
    </View>
  );
}
