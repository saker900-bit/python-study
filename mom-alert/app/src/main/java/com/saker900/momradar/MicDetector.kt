package com.saker900.momradar

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.SystemClock
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * 마이크로 "쿵" 하는 저음 충격(발소리)을 찾는다.
 * 소리는 저장하지 않고, 32ms마다 저음 대역의 크기(dB)만 계산한다.
 *
 * 주변 소음 크기(noise floor)를 계속 따라가면서, 그보다 [thresholdDb] 이상
 * 갑자기 커지는 순간을 충격 하나로 본다.
 */
class MicDetector(
    /** 충격 감지 (시간 ms, 세기). 마이크 스레드에서 호출됨. */
    private val onImpact: (Long, Double) -> Unit,
) {
    @Volatile var sensitivity: Int = 6

    /** 화면 표시용 최근 값 */
    @Volatile var levelDb: Double = Double.NaN; private set
    @Volatile var floorDb: Double = Double.NaN; private set

    @Volatile private var running = false
    private var thread: Thread? = null

    private val thresholdDb: Double get() = 22.0 - sensitivity * 1.6 // 감도 6 → 12.4dB, 10 → 6dB

    /** @return 마이크를 못 열면 false */
    @SuppressLint("MissingPermission") // 서비스 시작 전에 화면에서 권한을 확인함
    fun start(): Boolean {
        if (running) return true
        val minBuf = AudioRecord.getMinBufferSize(RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minBuf <= 0) return false
        val rec = try {
            AudioRecord(
                // 자동 볼륨 조절(AGC)이 없는 소스라 크기 비교가 안정적
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
                max(minBuf, FRAME * 2) * 4,
            )
        } catch (e: Exception) {
            return false
        }
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            rec.release()
            return false
        }
        running = true
        thread = Thread({ loop(rec) }, "mom-radar-mic").also { it.start() }
        return true
    }

    fun stop() {
        running = false
        thread?.join(500)
        thread = null
    }

    private fun loop(rec: AudioRecord) {
        try {
            rec.startRecording()
        } catch (e: Exception) {
            rec.release(); running = false; return
        }
        val buf = ShortArray(FRAME)
        val lp = Biquad.lowPass(RATE.toDouble(), 300.0) // 발소리는 대부분 300Hz 아래의 둔탁한 소리
        val startedAt = SystemClock.elapsedRealtime()
        var floor = Double.NaN
        var wasAbove = false

        while (running) {
            val n = rec.read(buf, 0, FRAME)
            if (n <= 0) {
                if (n < 0) break
                continue
            }
            var sum = 0.0
            for (i in 0 until n) {
                val y = lp.process(buf[i] / 32768.0)
                sum += y * y
            }
            val db = 20.0 * log10(sqrt(sum / n) + 1e-9)
            val now = SystemClock.elapsedRealtime()

            if (floor.isNaN()) floor = db
            val excess = db - floor
            val thr = thresholdDb
            val above = excess > thr
            // 막 켰을 때 1.5초는 주변 소음만 학습
            if (above && !wasAbove && now - startedAt > 1500) {
                onImpact(now, 10.0.pow(excess / 20.0))
            }
            wasAbove = excess > thr * 0.6 // 히스테리시스: 한 걸음을 두 번 세지 않게

            // 소음 기준선: 내려갈 땐 빠르게, 올라갈 땐 천천히 (지속되는 소음엔 적응, 짧은 쿵은 무시)
            floor += if (db < floor) 0.1 * (db - floor) else 0.004 * (db - floor)

            levelDb = db
            floorDb = floor
        }
        try { rec.stop() } catch (_: Exception) {}
        rec.release()
        running = false
    }

    /** 2차 IIR 필터 (RBJ cookbook). */
    private class Biquad(
        private val b0: Double, private val b1: Double, private val b2: Double,
        private val a1: Double, private val a2: Double,
    ) {
        private var x1 = 0.0; private var x2 = 0.0; private var y1 = 0.0; private var y2 = 0.0

        fun process(x: Double): Double {
            val y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2 = x1; x1 = x; y2 = y1; y1 = y
            return y
        }

        companion object {
            fun lowPass(rate: Double, cutoff: Double, q: Double = 0.7071): Biquad {
                val w0 = 2 * PI * cutoff / rate
                val alpha = sin(w0) / (2 * q)
                val c = cos(w0)
                val a0 = 1 + alpha
                return Biquad(
                    (1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0,
                    -2 * c / a0, (1 - alpha) / a0,
                )
            }
        }
    }

    companion object {
        private const val RATE = 16000
        private const val FRAME = 512 // 32ms
    }
}
