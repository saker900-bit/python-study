import AsyncStorage from "@react-native-async-storage/async-storage";

export type Settings = {
  lines: string[]; // 비어 있으면 전체
  notifyResolved: boolean;
  enabled: boolean;
  onboarded: boolean;
};

const KEY = "settings.v1";
export const DEFAULT_SETTINGS: Settings = {
  lines: [],
  notifyResolved: true,
  enabled: true,
  onboarded: false,
};

export async function loadSettings(): Promise<Settings> {
  const raw = await AsyncStorage.getItem(KEY);
  return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : DEFAULT_SETTINGS;
}

export async function saveSettings(s: Settings) {
  await AsyncStorage.setItem(KEY, JSON.stringify(s));
}
