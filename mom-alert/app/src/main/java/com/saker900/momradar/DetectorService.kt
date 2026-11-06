package com.saker900.momradar

import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock

/**
 * 백그라운드에서 마이크/진동을 감시하는 포그라운드 서비스.
 * 걸음 판정과 알림은 모두 메인 스레드에서 처리한다.
 */
class DetectorService : Service(), SharedPreferences.OnSharedPreferenceChangeListener {

    data class LiveStatus(
        val micOn: Boolean,
        val micDb: Double,
        val micFloorDb: Double,
        val micSteps: Int,
        val vibOn: Boolean,
        val vibPeak: Double,
        val vibFloor: Double,
        val vibSteps: Int,
        val handling: Boolean,
        val lastAlertAgoSec: Long?,
    )

    private val main = Handler(Looper.getMainLooper())
    private lateinit var prefs: Prefs

    private var mic: MicDetector? = null
    private var vib: VibrationDetector? = null
    private val micPattern = StepPattern()
    private val vibPattern = StepPattern()
    private var lastAlertAt = 0L
    private var wakeLock: PowerManager.WakeLock? = null
    private var notifText = ""

    private val ticker = object : Runnable {
        override fun run() {
            val now = SystemClock.elapsedRealtime()
            micPattern.tick(now)
            vibPattern.tick(now)
            publishStatus(now)
            main.postDelayed(this, 250)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        prefs = Prefs(this)
        Alerts.createChannels(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        notifText = "발소리를 기다리는 중…"
        val notification = Alerts.monitorNotification(this, notifText)
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(Alerts.ID_MONITOR, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            } else {
                startForeground(Alerts.ID_MONITOR, notification)
            }
        } catch (e: Exception) {
            // 권한이 없거나 백그라운드에서 시작된 경우
            stopSelf()
            return START_NOT_STICKY
        }
        if (!isRunning) {
            isRunning = true
            acquireWakeLock()
            prefs.sp.registerOnSharedPreferenceChangeListener(this)
            applySettings()
            main.post(ticker)
        }
        // 마이크는 앱 화면에서 켠 경우에만 쓸 수 있어서, 시스템이 자동 재시작하지 않게 함
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        isRunning = false
        main.removeCallbacks(ticker)
        prefs.sp.unregisterOnSharedPreferenceChangeListener(this)
        mic?.stop(); mic = null
        vib?.stop(); vib = null
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        statusListener?.invoke(null)
        super.onDestroy()
    }

    override fun onSharedPreferenceChanged(sp: SharedPreferences?, key: String?) {
        applySettings()
    }

    /** 설정을 읽어서 감지기를 켜고/끄고 감도를 맞춘다. */
    private fun applySettings() {
        micPattern.stepsNeeded = prefs.stepsNeeded
        micPattern.approachOnly = prefs.approachOnly
        vibPattern.stepsNeeded = prefs.stepsNeeded
        vibPattern.approachOnly = prefs.approachOnly

        if (prefs.micEnabled) {
            if (mic == null) {
                val d = MicDetector { t, s -> main.post { onImpact(micPattern, t, s, "발소리") } }
                if (d.start()) mic = d
            }
            mic?.sensitivity = prefs.micSensitivity
        } else {
            mic?.stop(); mic = null; micPattern.reset()
        }

        if (prefs.vibEnabled) {
            if (vib == null) {
                val d = VibrationDetector(
                    this,
                    onImpact = { t, s -> main.post { onImpact(vibPattern, t, s, "진동") } },
                    onHandling = { main.post { vibPattern.reset() } },
                )
                if (d.start()) vib = d else d.stop()
            }
            vib?.sensitivity = prefs.vibSensitivity
        } else {
            vib?.stop(); vib = null; vibPattern.reset()
        }
    }

    private fun onImpact(pattern: StepPattern, t: Long, strength: Double, source: String) {
        if (!isRunning) return
        if (!pattern.onImpact(t, strength)) return
        if (t - lastAlertAt < COOLDOWN_MS) return
        lastAlertAt = t
        micPattern.reset()
        vibPattern.reset()
        Alerts.fire(this, prefs.alertMessage, source)
    }

    private fun publishStatus(now: Long) {
        val m = mic
        val v = vib
        val status = LiveStatus(
            micOn = m != null,
            micDb = m?.levelDb ?: Double.NaN,
            micFloorDb = m?.floorDb ?: Double.NaN,
            micSteps = micPattern.count,
            vibOn = v != null,
            vibPeak = v?.peak ?: 0.0,
            vibFloor = v?.floor ?: Double.NaN,
            vibSteps = vibPattern.count,
            handling = v?.handling ?: false,
            lastAlertAgoSec = if (lastAlertAt == 0L) null else (now - lastAlertAt) / 1000,
        )
        statusListener?.invoke(status)

        val text = when {
            m == null && v == null -> "⚠️ 마이크·센서를 쓸 수 없어요"
            status.micSteps > 0 || status.vibSteps > 0 ->
                "👣 걸음 ${maxOf(status.micSteps, status.vibSteps)}/${prefs.stepsNeeded}"
            else -> "발소리를 기다리는 중…"
        }
        if (text != notifText) {
            notifText = text
            getSystemService(NotificationManager::class.java)
                .notify(Alerts.ID_MONITOR, Alerts.monitorNotification(this, text))
        }
    }

    private fun acquireWakeLock() {
        // 화면이 꺼져도 센서 값을 계속 받기 위해 CPU만 깨워 둠
        val pm = getSystemService(PowerManager::class.java)
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MomRadar:detect").apply {
            setReferenceCounted(false)
            acquire(12 * 60 * 60 * 1000L)
        }
    }

    companion object {
        const val ACTION_STOP = "com.saker900.momradar.STOP"
        private const val COOLDOWN_MS = 15_000L

        @Volatile var isRunning = false
            private set

        /** 화면에 실시간 상태를 보여주기 위한 콜백 (메인 스레드). null = 서비스 종료. */
        var statusListener: ((LiveStatus?) -> Unit)? = null
    }
}
