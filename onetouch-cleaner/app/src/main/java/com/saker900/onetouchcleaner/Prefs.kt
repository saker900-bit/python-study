package com.saker900.onetouchcleaner

import android.content.Context

/** 간단한 설정 저장소. */
class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var premium: Boolean
        get() = sp.getBoolean(KEY_PREMIUM, false)
        set(v) = sp.edit().putBoolean(KEY_PREMIUM, v).apply()

    var disclosureAccepted: Boolean
        get() = sp.getBoolean(KEY_DISCLOSURE, false)
        set(v) = sp.edit().putBoolean(KEY_DISCLOSURE, v).apply()

    var clearCache: Boolean
        get() = sp.getBoolean(KEY_CLEAR_CACHE, true)
        set(v) = sp.edit().putBoolean(KEY_CLEAR_CACHE, v).apply()

    /** 일반 앱 중 사용자가 '제외'로 바꾼 앱 */
    var excluded: Set<String>
        get() = sp.getStringSet(KEY_EXCLUDED, emptySet())!!.toSet()
        set(v) = sp.edit().putStringSet(KEY_EXCLUDED, v).apply()

    /** 시스템 앱 중 사용자가 '적용'으로 바꾼 앱 (시스템 앱은 기본 제외) */
    var included: Set<String>
        get() = sp.getStringSet(KEY_INCLUDED, emptySet())!!.toSet()
        set(v) = sp.edit().putStringSet(KEY_INCLUDED, v).apply()

    private companion object {
        const val KEY_PREMIUM = "premium"
        const val KEY_DISCLOSURE = "disclosure_accepted"
        const val KEY_CLEAR_CACHE = "clear_cache"
        const val KEY_EXCLUDED = "excluded"
        const val KEY_INCLUDED = "included"
    }
}
