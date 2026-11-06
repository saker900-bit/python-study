import { API_URL } from "./config";

export type Incident = {
  id: string;
  line: string | null; // lines.ts 의 id
  station: string | null;
  cause: string; // 예: "스크린도어 고장"
  status: "active" | "resolved";
  summary: string;
  first_seen: string; // ISO
  resolved_at: string | null;
  sources: { kind: string; url: string; title: string }[];
};

export type DevicePrefs = {
  expo_token: string;
  app_user_id: string;
  platform: string;
  lines: string[]; // 비어 있으면 전체 노선
  notify_resolved: boolean;
  enabled: boolean;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  incidents: (hours = 24) => req<Incident[]>(`/v1/incidents?hours=${hours}`),
  registerDevice: (prefs: DevicePrefs) =>
    req<{ ok: boolean }>("/v1/devices", { method: "POST", body: JSON.stringify(prefs) }),
};
