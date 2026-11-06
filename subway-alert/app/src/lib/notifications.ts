import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { Platform } from "react-native";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

/** 푸시 권한을 받고 Expo 푸시 토큰을 돌려준다. 실패하면 null. */
export async function getPushToken(): Promise<string | null> {
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("delay", {
      name: "지연 알림",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
    });
    await Notifications.setNotificationChannelAsync("resolved", {
      name: "복구 알림",
      importance: Notifications.AndroidImportance.DEFAULT,
    });
    await Notifications.setNotificationChannelAsync("billing", {
      name: "결제 안내",
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }
  if (!Device.isDevice) return null; // 시뮬레이터는 푸시 불가

  const current = await Notifications.getPermissionsAsync();
  let granted = current.granted;
  if (!granted) granted = (await Notifications.requestPermissionsAsync()).granted;
  if (!granted) return null;

  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  const token = await Notifications.getExpoPushTokenAsync({ projectId });
  return token.data;
}

/** 무료체험 종료 전에 유료 전환을 미리 알려주는 로컬 알림 */
export async function scheduleTrialEndReminder(trialEnd: Date, priceText: string) {
  const id = "trial-end-reminder";
  await Notifications.cancelScheduledNotificationAsync(id).catch(() => {});
  const remindAt = new Date(trialEnd.getTime() - 3 * 24 * 60 * 60 * 1000);
  if (remindAt.getTime() <= Date.now()) return;
  await Notifications.scheduleNotificationAsync({
    identifier: id,
    content: {
      title: "무료체험이 3일 후 끝나요",
      body: `${trialEnd.toLocaleDateString("ko-KR")}부터 ${priceText}이 자동 결제됩니다. 원치 않으면 스토어에서 구독을 해지하세요.`,
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DATE,
      date: remindAt,
      channelId: "billing",
    },
  });
}
