package com.saker900.onetouchcleaner

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.graphics.Bitmap
import androidx.core.graphics.drawable.toBitmap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class AppItem(
    val packageName: String,
    val label: String,
    val isSystem: Boolean,
    val icon: Bitmap?,
)

object AppRepository {
    /** 런처에 보이는 앱 목록 (자기 자신 제외). */
    suspend fun loadApps(context: Context): List<AppItem> = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        pm.queryIntentActivities(intent, 0)
            .map { it.activityInfo.applicationInfo }
            .distinctBy { it.packageName }
            .filter { it.packageName != context.packageName }
            .map { ai ->
                val isSystem = ai.flags and ApplicationInfo.FLAG_SYSTEM != 0 &&
                    ai.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP == 0
                AppItem(
                    packageName = ai.packageName,
                    label = ai.loadLabel(pm).toString(),
                    isSystem = isSystem,
                    icon = runCatching { ai.loadIcon(pm).toBitmap(96, 96) }.getOrNull(),
                )
            }
            .sortedWith(compareBy<AppItem> { it.isSystem }.thenBy { it.label.lowercase() })
    }

    fun isSelected(app: AppItem, prefs: Prefs): Boolean =
        if (app.isSystem) app.packageName in prefs.included
        else app.packageName !in prefs.excluded
}
