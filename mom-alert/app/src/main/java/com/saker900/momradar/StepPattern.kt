package com.saker900.momradar

/**
 * 개별 "쿵" 소리(충격)를 받아서, 그게 사람 걸음 패턴인지 판단한다.
 *
 * 걸음으로 보는 조건:
 *  - 충격 사이 간격이 [minGapMs]~[maxGapMs] (보통 걸음은 0.4~1초 간격)
 *  - [stepsNeeded]번 이상 이어짐
 *  - approachOnly 이면 뒤쪽 걸음이 앞쪽보다 대체로 세야 함 (다가오는 중)
 */
class StepPattern(
    var stepsNeeded: Int = 3,
    var approachOnly: Boolean = true,
    private val minGapMs: Long = 250,
    private val maxGapMs: Long = 1600,
) {
    private data class Step(val t: Long, var strength: Double)

    private val steps = ArrayDeque<Step>()

    /** 현재 연속으로 이어진 걸음 수 (화면 표시용). */
    val count: Int get() = steps.size

    /** 충격 하나를 넣는다. 걸음 패턴이 완성되면 true. */
    fun onImpact(timeMs: Long, strength: Double): Boolean {
        val last = steps.lastOrNull()
        if (last != null) {
            val gap = timeMs - last.t
            if (gap < minGapMs) {
                // 같은 걸음의 여운. 세기만 갱신.
                if (strength > last.strength) last.strength = strength
                return false
            }
            if (gap > maxGapMs) steps.clear() // 너무 오래 끊겼으면 새로 시작
        }
        steps.addLast(Step(timeMs, strength))
        while (steps.size > 8) steps.removeFirst()

        if (steps.size < stepsNeeded) return false
        val recent = steps.toList().takeLast(stepsNeeded)
        if (approachOnly && !isApproaching(recent)) return false
        return true
    }

    /** 일정 시간 아무 충격이 없으면 리셋. */
    fun tick(nowMs: Long) {
        val last = steps.lastOrNull() ?: return
        if (nowMs - last.t > maxGapMs) steps.clear()
    }

    fun reset() = steps.clear()

    private fun isApproaching(recent: List<Step>): Boolean {
        val half = recent.size / 2
        val first = recent.take(half).map { it.strength }.average()
        val second = recent.takeLast(half).map { it.strength }.average()
        // 약간 줄어드는 건 허용 (측정 오차). 확실히 멀어지는 것만 무시.
        return second >= first * 0.9
    }
}
