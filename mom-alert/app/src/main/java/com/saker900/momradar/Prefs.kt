package com.saker900.momradar

import android.content.Context
import android.content.SharedPreferences

/** 앱 설정. 감도는 1(둔감)~10(예민). */
class Prefs(context: Context) {
    val sp: SharedPreferences = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var micEnabled: Boolean
        get() = sp.getBoolean(KEY_MIC, true)
        set(v) = sp.edit().putBoolean(KEY_MIC, v).apply()

    var vibEnabled: Boolean
        get() = sp.getBoolean(KEY_VIB, true)
        set(v) = sp.edit().putBoolean(KEY_VIB, v).apply()

    var micSensitivity: Int
        get() = sp.getInt(KEY_MIC_SENS, 6)
        set(v) = sp.edit().putInt(KEY_MIC_SENS, v.coerceIn(1, 10)).apply()

    var vibSensitivity: Int
        get() = sp.getInt(KEY_VIB_SENS, 6)
        set(v) = sp.edit().putInt(KEY_VIB_SENS, v.coerceIn(1, 10)).apply()

    /** 몇 걸음이 연속으로 들려야 알림을 보낼지 (2~6). */
    var stepsNeeded: Int
        get() = sp.getInt(KEY_STEPS, 3)
        set(v) = sp.edit().putInt(KEY_STEPS, v.coerceIn(2, 6)).apply()

    /** 발소리가 점점 커질 때(다가올 때)만 알림. */
    var approachOnly: Boolean
        get() = sp.getBoolean(KEY_APPROACH, true)
        set(v) = sp.edit().putBoolean(KEY_APPROACH, v).apply()

    var alertMessage: String
        get() = sp.getString(KEY_MSG, null)?.takeIf { it.isNotBlank() } ?: DEFAULT_MESSAGE
        set(v) = sp.edit().putString(KEY_MSG, v).apply()

    companion object {
        const val KEY_MIC = "mic"
        const val KEY_VIB = "vib"
        const val KEY_MIC_SENS = "mic_sens"
        const val KEY_VIB_SENS = "vib_sens"
        const val KEY_STEPS = "steps"
        const val KEY_APPROACH = "approach"
        const val KEY_MSG = "msg"
        const val DEFAULT_MESSAGE = "엄마떴다!"
    }
}
