import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { AppProvider, useApp } from "../lib/AppContext";

function FirstRunGate() {
  const { ready, settings, sub, updateSettings } = useApp();
  useEffect(() => {
    if (ready && !settings.onboarded) {
      updateSettings({ onboarded: true });
      if (!sub?.active) router.push("/paywall");
    }
  }, [ready, settings.onboarded, sub?.active, updateSettings]);
  return null;
}

export default function RootLayout() {
  return (
    <AppProvider>
      <StatusBar style="dark" />
      <FirstRunGate />
      <Stack screenOptions={{ headerTitleStyle: { fontWeight: "700" } }}>
        <Stack.Screen name="index" options={{ title: "지하철 지연알림" }} />
        <Stack.Screen name="settings" options={{ title: "설정" }} />
        <Stack.Screen name="paywall" options={{ presentation: "modal", headerShown: false }} />
      </Stack>
    </AppProvider>
  );
}
