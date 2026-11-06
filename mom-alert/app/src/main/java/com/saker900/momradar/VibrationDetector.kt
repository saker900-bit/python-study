package com.saker900.momradar

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * 가속도 센서로 바닥/책상을 타고 오는 진동(쿵쿵)을 찾는다.
 * 폰이 바닥이나 책상에 놓여 있을 때만 의미가 있고,
 * 손에 들고 움직이는 중이면 자동으로 감지를 쉰다.
 */
class VibrationDetector(
    context: Context,
    /** 충격 감지 (시간 ms, 세기). 센서 스레드에서 호출됨. */
    private val onImpact: (Long, Double) -> Unit,
    /** 폰을 들고 움직이기 시작함 → 걸음 패턴 리셋용 */
    private val onHandling: () -> Unit,
) : SensorEventListener {

    @Volatile var sensitivity: Int = 6

    @Volatile var peak: Double = 0.0; private set
    @Volatile var floor: Double = Double.NaN; private set
    @Volatile var handling: Boolean = false; private set

    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accel: Sensor? = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private var thread: HandlerThread? = null

    private var gravity = Double.NaN
    private var windowStart = 0L
    private var windowPeak = 0.0
    private var wasAbove = false
    private var handlingUntil = 0L
    private var startedAt = 0L

    private val factor: Double get() = 6.5 - sensitivity * 0.5 // 감도 6 → 기준선의 3.5배, 10 → 1.5배

    fun start(): Boolean {
        val sensor = accel ?: return false
        if (thread != null) return true
        gravity = Double.NaN; floor = Double.NaN; windowPeak = 0.0; wasAbove = false
        startedAt = SystemClock.elapsedRealtime()
        windowStart = startedAt
        val t = HandlerThread("mom-radar-accel").also { it.start() }
        thread = t
        // 100Hz. (안드로이드 12+는 권한 없이 200Hz까지만 허용)
        return sm.registerListener(this, sensor, 10_000, Handler(t.looper))
    }

    fun stop() {
        sm.unregisterListener(this)
        thread?.quitSafely()
        thread = null
    }

    override fun onSensorChanged(e: SensorEvent) {
        val m = sqrt((e.values[0] * e.values[0] + e.values[1] * e.values[1] + e.values[2] * e.values[2]).toDouble())
        if (gravity.isNaN()) gravity = m
        gravity += 0.02 * (m - gravity)
        val dev = abs(m - gravity)
        val now = SystemClock.elapsedRealtime()

        // 손에 들고 있음 (큰 움직임) → 2초간 감지 중지
        if (dev > HANDLING_THRESHOLD) {
            if (now >= handlingUntil) onHandling()
            handlingUntil = now + 2000
        }
        handling = now < handlingUntil

        windowPeak = max(windowPeak, dev)
        if (now - windowStart < WINDOW_MS) return

        // 50ms 구간 하나 처리
        val p = windowPeak
        windowPeak = 0.0
        windowStart = now
        peak = p
        if (handling) {
            wasAbove = true // 들고 있다 내려놓는 순간을 걸음으로 세지 않게
            return
        }
        var f = floor
        if (f.isNaN()) f = p
        val thr = max(f * factor, MIN_ABS)
        if (p > thr && !wasAbove && now - startedAt > 1500) {
            onImpact(now, p)
        }
        wasAbove = p > max(f * factor * 0.6, MIN_ABS)
        f += if (p < f) 0.1 * (p - f) else 0.01 * (p - f)
        floor = max(f, 0.0005)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    companion object {
        private const val WINDOW_MS = 50L
        private const val MIN_ABS = 0.012 // m/s², 센서 잡음보다 확실히 큰 값
        private const val HANDLING_THRESHOLD = 0.8 // m/s²
    }
}
