package com.yeonrak.app;

import android.app.Activity;
import android.content.Intent;
import android.webkit.JavascriptInterface;

/** 웹 화면(JS)에서 window.Android.* 로 부르는 네이티브 기능. */
public class Bridge {
    private final Activity activity;

    Bridge(Activity activity) {
        this.activity = activity;
    }

    /** atMillis 시각에 알림 예약. 같은 id 로 다시 부르면 덮어쓴다. */
    @JavascriptInterface
    public void schedule(String id, double atMillis, String title, String body) {
        ReminderReceiver.save(activity, id, (long) atMillis, title, body);
        ReminderReceiver.arm(activity, id, (long) atMillis, title, body);
    }

    @JavascriptInterface
    public void cancel(String id) {
        ReminderReceiver.cancel(activity, id);
    }

    /** 카톡 등으로 메시지 보내기 (공유 시트). */
    @JavascriptInterface
    public void share(final String text) {
        activity.runOnUiThread(new Runnable() {
            public void run() {
                Intent send = new Intent(Intent.ACTION_SEND);
                send.setType("text/plain");
                send.putExtra(Intent.EXTRA_TEXT, text);
                activity.startActivity(Intent.createChooser(send, "누구한테 재촉할까요?"));
            }
        });
    }

    @JavascriptInterface
    public void notifyNow(String title, String body) {
        ReminderReceiver.show(activity, "now" + System.currentTimeMillis(), title, body);
    }
}
