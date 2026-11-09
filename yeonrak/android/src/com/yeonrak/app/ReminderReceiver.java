package com.yeonrak.app;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.util.Iterator;

/** 예약된 시각에 알림을 띄운다. 재부팅되면 예약을 다시 건다. */
public class ReminderReceiver extends BroadcastReceiver {
    private static final String PREFS = "alarms";
    private static final String CHANNEL = "remind";

    @Override
    public void onReceive(Context ctx, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            rearmAll(ctx);
            return;
        }
        String id = intent.getStringExtra("id");
        show(ctx, id, intent.getStringExtra("title"), intent.getStringExtra("body"));
        prefs(ctx).edit().remove(id).apply();
    }

    static SharedPreferences prefs(Context ctx) {
        return ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static void save(Context ctx, String id, long at, String title, String body) {
        try {
            JSONObject o = new JSONObject();
            o.put("at", at);
            o.put("title", title);
            o.put("body", body);
            prefs(ctx).edit().putString(id, o.toString()).apply();
        } catch (Exception ignored) {
        }
    }

    static PendingIntent pending(Context ctx, String id, String title, String body) {
        Intent i = new Intent(ctx, ReminderReceiver.class);
        i.setAction("com.yeonrak.app.REMIND." + id);
        i.putExtra("id", id);
        i.putExtra("title", title);
        i.putExtra("body", body);
        return PendingIntent.getBroadcast(ctx, id.hashCode(), i,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    static void arm(Context ctx, String id, long at, String title, String body) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        long when = Math.max(at, System.currentTimeMillis() + 1000);
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, when, pending(ctx, id, title, body));
    }

    static void cancel(Context ctx, String id) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        am.cancel(pending(ctx, id, "", ""));
        prefs(ctx).edit().remove(id).apply();
    }

    static void rearmAll(Context ctx) {
        Iterator<String> it = prefs(ctx).getAll().keySet().iterator();
        while (it.hasNext()) {
            String id = it.next();
            try {
                JSONObject o = new JSONObject(prefs(ctx).getString(id, "{}"));
                arm(ctx, id, o.getLong("at"), o.getString("title"), o.getString("body"));
            } catch (Exception ignored) {
            }
        }
    }

    static void show(Context ctx, String id, String title, String body) {
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL, "연락 알림", NotificationManager.IMPORTANCE_HIGH));
        Intent open = new Intent(ctx, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(ctx, 0, open,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        Notification n = new Notification.Builder(ctx, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_popup_reminder)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new Notification.BigTextStyle().bigText(body))
                .setContentIntent(pi)
                .setAutoCancel(true)
                .build();
        nm.notify(id == null ? 0 : id.hashCode(), n);
    }
}
