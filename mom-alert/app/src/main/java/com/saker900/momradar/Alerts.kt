package com.saker900.momradar

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.os.Build
import android.os.VibrationAttributes
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

object Alerts {
    const val CH_MONITOR = "monitor"
    const val CH_ALERT = "alert_v1"
    const val ID_MONITOR = 1
    private const val ID_ALERT = 2

    private val PATTERN = longArrayOf(0, 400, 150, 400, 150, 700)

    fun createChannels(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CH_MONITOR, "감시 중 표시", NotificationManager.IMPORTANCE_LOW).apply {
                description = "레이더가 켜져 있는 동안 표시되는 알림"
                setShowBadge(false)
            }
        )
        nm.createNotificationChannel(
            NotificationChannel(CH_ALERT, "누가 온다! 알림", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "다가오는 발소리를 감지했을 때"
                enableVibration(true)
                vibrationPattern = PATTERN
                setSound(null, null) // 소리 나면 들키니까 진동만
            }
        )
    }

    private fun openAppIntent(ctx: Context): PendingIntent =
        PendingIntent.getActivity(
            ctx, 0,
            Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

    fun monitorNotification(ctx: Context, text: String): Notification {
        val stop = PendingIntent.getService(
            ctx, 1,
            Intent(ctx, DetectorService::class.java).setAction(DetectorService.ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return Notification.Builder(ctx, CH_MONITOR)
            .setSmallIcon(R.drawable.ic_stat_radar)
            .setContentTitle("📡 엄마레이더 감시 중")
            .setContentText(text)
            .setOngoing(true)
            .setContentIntent(openAppIntent(ctx))
            .addAction(Notification.Action.Builder(null, "끄기", stop).build())
            .build()
    }

    /** 경고! 알림 + 진동. */
    fun fire(ctx: Context, message: String, source: String) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        val n = Notification.Builder(ctx, CH_ALERT)
            .setSmallIcon(R.drawable.ic_stat_radar)
            .setContentTitle("🚨 $message")
            .setContentText("$source 감지됨 · 누가 다가오고 있어요")
            .setCategory(Notification.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setTimeoutAfter(30_000)
            .setContentIntent(openAppIntent(ctx))
            .build()
        try {
            nm.notify(ID_ALERT, n)
        } catch (_: SecurityException) {
            // 알림 권한이 없어도 진동은 울린다
        }
        vibrate(ctx)
    }

    @Suppress("DEPRECATION")
    private fun vibrate(ctx: Context) {
        val vib: Vibrator = if (Build.VERSION.SDK_INT >= 31) {
            ctx.getSystemService(VibratorManager::class.java).defaultVibrator
        } else {
            ctx.getSystemService(Vibrator::class.java)
        }
        if (!vib.hasVibrator()) return
        val effect = VibrationEffect.createWaveform(PATTERN, -1)
        if (Build.VERSION.SDK_INT >= 33) {
            vib.vibrate(effect, VibrationAttributes.createForUsage(VibrationAttributes.USAGE_ALARM))
        } else {
            vib.vibrate(
                effect,
                AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).build(),
            )
        }
    }
}
