package com.saker900.onetouchcleaner

import android.accessibilityservice.AccessibilityService
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.net.Uri
import android.os.SystemClock
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * 선택한 앱마다 시스템 '앱 정보' 화면을 열고
 * [강제 종료] → [확인], [저장공간] → [캐시 지우기] 버튼을 대신 눌러준다.
 *
 * 안드로이드는 일반 앱이 다른 앱을 직접 종료하거나 캐시를 지우는 API를 막아두었기 때문에,
 * 사용자가 직접 누르는 것과 같은 동작을 접근성 서비스로 수행하는 방식이다.
 * 제조사(삼성/픽셀/샤오미 등)와 언어별 버튼 이름을 함께 찾는다.
 */
class CleanerService : AccessibilityService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var job: Job? = null
    private var overlay: View? = null
    private var overlayText: TextView? = null

    override fun onServiceConnected() {
        instance = this
    }

    override fun onUnbind(intent: Intent?): Boolean {
        instance = null
        job?.cancel()
        removeOverlay()
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        instance = null
        removeOverlay()
        scope.cancel()
        super.onDestroy()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit
    override fun onInterrupt() = Unit

    fun start(targets: List<CleanTarget>, clearCache: Boolean) {
        if (job?.isActive == true || targets.isEmpty()) return
        job = scope.launch {
            var r = CleanResult(total = targets.size)
            showOverlay()
            try {
                targets.forEachIndexed { i, t ->
                    CleanerState.set(CleanStatus.Running(i + 1, targets.size, t.label))
                    overlayText?.text = "정리 중… ${i + 1} / ${targets.size}\n${t.label}"
                    r = when (processApp(t, clearCache)) {
                        Outcome.STOPPED -> r.copy(stopped = r.stopped + 1)
                        Outcome.STOPPED_AND_CACHE -> r.copy(stopped = r.stopped + 1, cacheCleared = r.cacheCleared + 1)
                        Outcome.NOT_RUNNING -> r.copy(notRunning = r.notRunning + 1)
                        Outcome.NOT_RUNNING_CACHE -> r.copy(notRunning = r.notRunning + 1, cacheCleared = r.cacheCleared + 1)
                        Outcome.FAILED -> r.copy(failed = r.failed + 1)
                    }
                }
            } catch (e: CancellationException) {
                r = r.copy(cancelled = true)
            } finally {
                removeOverlay()
                CleanerState.set(CleanStatus.Done(r))
                returnToApp()
            }
        }
    }

    fun cancel() {
        job?.cancel()
    }

    // ---------------------------------------------------------------- 앱 하나 처리

    private enum class Outcome { STOPPED, STOPPED_AND_CACHE, NOT_RUNNING, NOT_RUNNING_CACHE, FAILED }

    private suspend fun processApp(t: CleanTarget, clearCache: Boolean): Outcome {
        openAppDetails(t.packageName)
        delay(STEP_DELAY)

        // 해당 앱의 정보 화면이 떴는지 확인 (앱 이름이 보이고 강제 종료 버튼이 있어야 함)
        val forceStop = waitFor(PAGE_TIMEOUT) { root ->
            if (root.findAccessibilityNodeInfosByText(t.label).isNullOrEmpty()) null
            else findById(root, FORCE_STOP_IDS) ?: findByText(root, FORCE_STOP_LABELS)
        } ?: return Outcome.FAILED

        var stopped = false
        val btn = clickableOf(forceStop)
        if (btn != null && btn.isEnabled) {
            btn.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            // 확인 다이얼로그
            val ok = waitFor(DIALOG_TIMEOUT) { root ->
                findById(root, CONFIRM_IDS) ?: findByText(root, CONFIRM_LABELS, exact = true)
            }
            if (ok != null) {
                clickableOf(ok)?.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                stopped = true
                delay(STEP_DELAY)
            }
        }

        var cache = false
        if (clearCache) cache = clearCacheOnCurrentPage()

        return when {
            stopped && cache -> Outcome.STOPPED_AND_CACHE
            stopped -> Outcome.STOPPED
            cache -> Outcome.NOT_RUNNING_CACHE
            else -> Outcome.NOT_RUNNING
        }
    }

    private suspend fun clearCacheOnCurrentPage(): Boolean {
        val storage = waitFor(PAGE_TIMEOUT, scroll = true) { root ->
            // 권한 요약(예: "카메라, 저장공간")을 잘못 누르지 않도록 정확히 일치하는 항목만
            findByText(root, STORAGE_LABELS, exact = true)
        } ?: return false
        clickableOf(storage)?.performAction(AccessibilityNodeInfo.ACTION_CLICK) ?: return false
        delay(STEP_DELAY)

        val clear = waitFor(PAGE_TIMEOUT) { root ->
            findById(root, CLEAR_CACHE_IDS) ?: findByText(root, CLEAR_CACHE_LABELS)
        } ?: return false
        val btn = clickableOf(clear) ?: return false
        if (!btn.isEnabled) return false // 이미 캐시가 비어 있음
        btn.performAction(AccessibilityNodeInfo.ACTION_CLICK)
        delay(STEP_DELAY)
        // 일부 기기는 확인 다이얼로그를 띄움
        waitFor(800) { root -> findById(root, CONFIRM_IDS) }
            ?.let { clickableOf(it)?.performAction(AccessibilityNodeInfo.ACTION_CLICK) }
        return true
    }

    // ---------------------------------------------------------------- 화면 조작 도우미

    private fun openAppDetails(pkg: String) {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$pkg"))
            .addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TASK or
                    Intent.FLAG_ACTIVITY_NO_ANIMATION or
                    Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
            )
        startActivity(intent)
    }

    private fun returnToApp() {
        performGlobalAction(GLOBAL_ACTION_BACK)
        val intent = Intent(this, MainActivity::class.java).addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        )
        startActivity(intent)
    }

    /** 우리 앱/오버레이/시스템UI를 뺀, 위에 있는 창부터 루트 노드를 돌려준다. */
    private fun targetRoots(): List<AccessibilityNodeInfo> {
        val list = runCatching {
            windows
                .filter { it.type != AccessibilityWindowInfo.TYPE_ACCESSIBILITY_OVERLAY }
                .sortedByDescending { it.layer }
                .mapNotNull { it.root }
                .filter {
                    val p = it.packageName?.toString()
                    p != packageName && p != "com.android.systemui"
                }
        }.getOrDefault(emptyList())
        if (list.isNotEmpty()) return list
        return listOfNotNull(rootInActiveWindow)
    }

    private suspend fun waitFor(
        timeoutMs: Long,
        scroll: Boolean = false,
        finder: (AccessibilityNodeInfo) -> AccessibilityNodeInfo?,
    ): AccessibilityNodeInfo? {
        val end = SystemClock.uptimeMillis() + timeoutMs
        var scrolls = 0
        while (SystemClock.uptimeMillis() < end) {
            val roots = targetRoots()
            for (root in roots) finder(root)?.let { return it }
            if (scroll && scrolls < MAX_SCROLLS && roots.isNotEmpty()) {
                findScrollable(roots.first())?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                scrolls++
            }
            delay(POLL)
        }
        return null
    }

    private fun findById(root: AccessibilityNodeInfo, ids: List<String>): AccessibilityNodeInfo? {
        for (id in ids) {
            val nodes = runCatching { root.findAccessibilityNodeInfosByViewId(id) }.getOrNull() ?: continue
            nodes.firstOrNull { it.isVisibleToUser }?.let { return it }
            nodes.firstOrNull()?.let { return it }
        }
        return null
    }

    private fun findByText(
        root: AccessibilityNodeInfo,
        labels: List<String>,
        exact: Boolean = false,
    ): AccessibilityNodeInfo? {
        for (label in labels) {
            val nodes = runCatching { root.findAccessibilityNodeInfosByText(label) }.getOrNull() ?: continue
            val matches = nodes.filter {
                val txt = (it.text ?: it.contentDescription)?.toString()?.trim() ?: return@filter false
                if (exact) txt.equals(label, ignoreCase = true) else txt.contains(label, ignoreCase = true)
            }
            // 정확히 일치하는 것을 우선
            (matches.firstOrNull { (it.text ?: "").toString().trim().equals(label, true) } ?: matches.firstOrNull())
                ?.let { return it }
        }
        return null
    }

    private fun clickableOf(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        var n: AccessibilityNodeInfo? = node
        var depth = 0
        while (n != null && depth < 6) {
            if (n.isClickable) return n
            n = n.parent
            depth++
        }
        return null
    }

    private fun findScrollable(root: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        val queue = ArrayDeque<AccessibilityNodeInfo>()
        queue.add(root)
        var visited = 0
        while (queue.isNotEmpty() && visited < 400) {
            val n = queue.removeFirst()
            visited++
            if (n.isScrollable) return n
            for (i in 0 until n.childCount) n.getChild(i)?.let { queue.add(it) }
        }
        return null
    }

    // ---------------------------------------------------------------- 진행 오버레이

    private fun showOverlay() {
        if (overlay != null) return
        val wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val dp = resources.displayMetrics.density
        val text = TextView(this).apply {
            setTextColor(Color.WHITE)
            textSize = 18f
            gravity = Gravity.CENTER
            text = "정리 준비 중…"
        }
        val stop = Button(this).apply {
            text = "중지"
            setOnClickListener { cancel() }
        }
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.argb(235, 15, 23, 42))
            setPadding((24 * dp).toInt(), (24 * dp).toInt(), (24 * dp).toInt(), (24 * dp).toInt())
            addView(ProgressBar(this@CleanerService))
            addView(text, LinearLayout.LayoutParams(-2, -2).apply { topMargin = (16 * dp).toInt() })
            addView(stop, LinearLayout.LayoutParams(-2, -2).apply { topMargin = (24 * dp).toInt() })
        }
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            // 포커스를 가져가지 않아야 아래 설정 화면이 '활성 창'으로 유지된다.
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        )
        runCatching {
            wm.addView(layout, lp)
            overlay = layout
            overlayText = text
        }
    }

    private fun removeOverlay() {
        val v = overlay ?: return
        runCatching { (getSystemService(Context.WINDOW_SERVICE) as WindowManager).removeView(v) }
        overlay = null
        overlayText = null
    }

    companion object {
        @Volatile
        var instance: CleanerService? = null
            private set

        fun isEnabled(context: Context): Boolean {
            val me = ComponentName(context, CleanerService::class.java).flattenToString()
            val enabled = Settings.Secure.getString(
                context.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: return false
            return enabled.split(':').any { it.equals(me, ignoreCase = true) }
        }

        private const val POLL = 150L
        private const val STEP_DELAY = 450L
        private const val PAGE_TIMEOUT = 4000L
        private const val DIALOG_TIMEOUT = 2500L
        private const val MAX_SCROLLS = 3

        private val FORCE_STOP_IDS = listOf(
            "com.android.settings:id/force_stop_button",
            "com.android.settings:id/right_button",
        )
        private val FORCE_STOP_LABELS = listOf(
            "강제 종료", "강제 중지", "강제종료", "강제중지",
            "Force stop", "Force close",
        )
        private val CONFIRM_IDS = listOf("android:id/button1")
        private val CONFIRM_LABELS = listOf("확인", "OK")

        private val STORAGE_LABELS = listOf(
            "저장공간 및 캐시", "저장 공간 및 캐시", "저장용량 및 캐시",
            "저장공간", "저장 공간", "저장용량",
            "Storage & cache", "Storage and cache", "Storage",
        )
        private val CLEAR_CACHE_IDS = listOf(
            "com.android.settings:id/button2",
            "com.android.settings:id/clear_cache_button",
        )
        private val CLEAR_CACHE_LABELS = listOf(
            "캐시 지우기", "캐시 삭제", "캐시 비우기", "Clear cache",
        )
    }
}
