import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import { api } from "./api";
import { getPushToken } from "./notifications";
import { getSubState, initPurchases, onSubChange, type SubState } from "./purchases";
import { DEFAULT_SETTINGS, loadSettings, saveSettings, type Settings } from "./storage";

type Ctx = {
  ready: boolean;
  sub: SubState | null;
  setSub: (s: SubState) => void;
  settings: Settings;
  updateSettings: (patch: Partial<Settings>) => Promise<void>;
  pushToken: string | null;
  refreshPush: () => Promise<void>;
};

const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [sub, setSub] = useState<SubState | null>(null);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [pushToken, setPushToken] = useState<string | null>(null);
  const uid = useRef<string>("");

  useEffect(() => {
    (async () => {
      try {
        uid.current = await initPurchases();
        const [s, st] = await Promise.all([loadSettings(), getSubState()]);
        setSettings(s);
        setSub(st);
      } catch (e) {
        console.warn("init failed", e);
      } finally {
        setReady(true);
      }
    })();
    return onSubChange(setSub);
  }, []);

  // 설정/토큰이 바뀌면 서버에 동기화 (구독 여부는 서버가 RevenueCat 웹훅으로 직접 확인)
  useEffect(() => {
    if (!pushToken || !uid.current) return;
    api
      .registerDevice({
        expo_token: pushToken,
        app_user_id: uid.current,
        platform: Platform.OS,
        lines: settings.lines,
        notify_resolved: settings.notifyResolved,
        enabled: settings.enabled,
      })
      .catch((e) => console.warn("device sync failed", e));
  }, [pushToken, settings.lines, settings.notifyResolved, settings.enabled]);

  const refreshPush = useCallback(async () => {
    try {
      setPushToken(await getPushToken());
    } catch (e) {
      console.warn("push token failed", e);
    }
  }, []);

  useEffect(() => {
    if (ready && sub?.active) refreshPush();
  }, [ready, sub?.active, refreshPush]);

  const updateSettings = useCallback(async (patch: Partial<Settings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      saveSettings(next);
      return next;
    });
  }, []);

  return (
    <AppCtx.Provider value={{ ready, sub, setSub, settings, updateSettings, pushToken, refreshPush }}>
      {children}
    </AppCtx.Provider>
  );
}

export function useApp() {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useApp outside AppProvider");
  return c;
}
