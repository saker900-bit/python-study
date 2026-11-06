package com.saker900.onetouchcleaner

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.lifecycle.compose.collectAsStateWithLifecycle

class MainActivity : ComponentActivity() {

    private val vm: MainViewModel by viewModels()
    private val app get() = application as CleanerApp
    private var serviceEnabled by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        if (!app.prefs.premium) AdsManager.init(this)
        setContent {
            AppTheme { MainScreen() }
        }
    }

    override fun onResume() {
        super.onResume()
        serviceEnabled = CleanerService.isEnabled(this)
    }

    // ------------------------------------------------------------------ 동작

    private fun openAccessibilitySettings() {
        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    private fun openOwnAppInfo() {
        startActivity(
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    }

    private fun runClean() {
        val targets = vm.targets()
        val service = CleanerService.instance
        if (service == null) {
            toast("접근성 서비스가 꺼져 있어요. 다시 켜주세요.")
            serviceEnabled = false
            return
        }
        service.start(targets, vm.clearCache.value)
    }

    private fun onStartClicked(showDisclosure: () -> Unit) {
        if (!serviceEnabled) {
            showDisclosure()
            return
        }
        if (vm.targets().isEmpty()) {
            toast("정리할 앱을 1개 이상 선택하세요.")
            return
        }
        if (app.billing.premium.value) {
            runClean()
        } else {
            // 광고를 못 불러온 경우에도 사용자를 막지 않고 실행
            AdsManager.show(this, onRewarded = ::runClean, onUnavailable = ::runClean)
        }
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

    // ------------------------------------------------------------------ 화면

    @OptIn(ExperimentalMaterial3Api::class)
    @Composable
    private fun MainScreen() {
        val apps by vm.apps.collectAsStateWithLifecycle()
        val loading by vm.loading.collectAsStateWithLifecycle()
        val selected by vm.selected.collectAsStateWithLifecycle()
        val clearCache by vm.clearCache.collectAsStateWithLifecycle()
        val premium by app.billing.premium.collectAsStateWithLifecycle()
        val price by app.billing.price.collectAsStateWithLifecycle()
        val status by CleanerState.status.collectAsStateWithLifecycle()

        var query by rememberSaveable { mutableStateOf("") }
        var showSystem by rememberSaveable { mutableStateOf(false) }
        var disclosure by remember { mutableStateOf(false) }

        val visible = apps.filter {
            (showSystem || !it.isSystem) &&
                (query.isBlank() || it.label.contains(query, true) || it.packageName.contains(query, true))
        }
        val count = apps.count { it.packageName in selected && (showSystem || !it.isSystem) }

        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("원터치 클리너", fontWeight = FontWeight.Bold) },
                    actions = {
                        if (premium) {
                            Icon(Icons.Filled.Star, null, tint = Color(0xFFFFB300))
                            Text(" 광고 없음", fontSize = 13.sp, modifier = Modifier.padding(end = 16.dp))
                        }
                    },
                )
            },
        ) { pad ->
            Column(
                Modifier
                    .padding(pad)
                    .fillMaxSize()
                    .padding(horizontal = 16.dp)
            ) {
                if (!serviceEnabled) PermissionCard { disclosure = true }

                Button(
                    onClick = { onStartClicked { disclosure = true } },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(64.dp),
                    shape = RoundedCornerShape(16.dp),
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("정리 시작 · ${selected.size}개 앱", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        if (!premium) Text("광고 1회 시청 후 실행", fontSize = 12.sp)
                    }
                }

                Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("실행 중인 앱 종료 + 캐시 삭제", Modifier.weight(1f), fontSize = 14.sp)
                    Switch(checked = clearCache, onCheckedChange = vm::setClearCache)
                }

                if (!premium) {
                    OutlinedButton(
                        onClick = { if (!app.billing.buy(this@MainActivity)) toast("스토어 연결 중이에요. 잠시 후 다시 시도하세요.") },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("광고 평생 제거 · ${price ?: "₩5,900"}") }
                }

                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    leadingIcon = { Icon(Icons.Filled.Search, null) },
                    placeholder = { Text("앱 검색") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    FilterChip(selected = showSystem, onClick = { showSystem = !showSystem }, label = { Text("시스템 앱") })
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = { vm.setChecked(visible, true) }) { Text("전체 적용") }
                    TextButton(onClick = { vm.setChecked(visible, false) }) { Text("전체 제외") }
                }
                Text(
                    "체크 = 적용 / 해제 = 제외 · 화면 기준 $count 개 선택됨",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                if (loading) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
                } else {
                    LazyColumn(Modifier.fillMaxSize()) {
                        items(visible, key = { it.packageName }) { a ->
                            AppRow(a, a.packageName in selected) { vm.toggle(a, it) }
                            HorizontalDivider()
                        }
                    }
                }
            }
        }

        if (disclosure) DisclosureDialog(
            onAccept = {
                disclosure = false
                app.prefs.disclosureAccepted = true
                openAccessibilitySettings()
            },
            onDismiss = { disclosure = false },
        )

        when (val s = status) {
            is CleanStatus.Running -> AlertDialog(
                onDismissRequest = {},
                confirmButton = { TextButton(onClick = { CleanerService.instance?.cancel() }) { Text("중지") } },
                title = { Text("정리 중…") },
                text = { Text("${s.index} / ${s.total}  ${s.label}") },
            )
            is CleanStatus.Done -> ResultDialog(s.result) { CleanerState.reset() }
            CleanStatus.Idle -> Unit
        }
    }

    @Composable
    private fun PermissionCard(onClick: () -> Unit) {
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
            modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
        ) {
            Column(Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Warning, null)
                    Text("  접근성 권한이 필요해요", fontWeight = FontWeight.Bold)
                }
                Text(
                    "앱 종료와 캐시 삭제 버튼을 대신 눌러주려면 '원터치 클리너' 접근성 서비스를 켜야 해요.",
                    fontSize = 13.sp,
                    modifier = Modifier.padding(vertical = 6.dp),
                )
                Button(onClick = onClick) { Text("권한 켜기") }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    Text(
                        "‘제한된 설정’이라고 나오면: 앱 정보 → 오른쪽 위 ⋮ → ‘제한된 설정 허용’ 후 다시 켜주세요.",
                        fontSize = 12.sp,
                        modifier = Modifier.padding(top = 6.dp).clickable { openOwnAppInfo() },
                    )
                }
            }
        }
    }

    @Composable
    private fun AppRow(a: AppItem, checked: Boolean, onChange: (Boolean) -> Unit) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable { onChange(!checked) }
                .padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            a.icon?.let { Image(it.asImageBitmap(), null, Modifier.size(40.dp)) }
                ?: Spacer(Modifier.size(40.dp))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(a.label, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    a.packageName + if (a.isSystem) " · 시스템" else "",
                    fontSize = 11.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Checkbox(checked = checked, onCheckedChange = onChange)
        }
    }

    /** Play 정책: 접근성 API 사용 전 '명시적 고지 + 동의' 필수 */
    @Composable
    private fun DisclosureDialog(onAccept: () -> Unit, onDismiss: () -> Unit) {
        AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text("접근성 서비스 사용 안내") },
            text = {
                Text(
                    "원터치 클리너는 접근성 서비스(AccessibilityService API)를 사용합니다.\n\n" +
                        "• 용도: 사용자가 ‘정리 시작’을 누를 때에만, 선택한 앱의 ‘앱 정보’ 화면을 열어 " +
                        "‘강제 종료’와 ‘캐시 지우기’ 버튼을 대신 누릅니다.\n" +
                        "• 화면 내용, 개인정보, 입력 내용을 수집·저장·전송하지 않습니다.\n" +
                        "• 언제든 설정에서 끌 수 있습니다.\n\n" +
                        "동의하면 접근성 설정 화면으로 이동합니다. ‘원터치 클리너’를 찾아 켜주세요."
                )
            },
            confirmButton = { Button(onClick = onAccept) { Text("동의하고 계속") } },
            dismissButton = { TextButton(onClick = onDismiss) { Text("취소") } },
        )
    }

    @Composable
    private fun ResultDialog(r: CleanResult, onClose: () -> Unit) {
        AlertDialog(
            onDismissRequest = onClose,
            title = { Text(if (r.cancelled) "정리 중지됨" else "정리 완료 ✨") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("대상 앱: ${r.total}개")
                    Text("종료한 앱: ${r.stopped}개")
                    Text("이미 꺼져 있던 앱: ${r.notRunning}개")
                    Text("캐시 삭제: ${r.cacheCleared}개")
                    if (r.failed > 0) Text("처리 못한 앱: ${r.failed}개", color = MaterialTheme.colorScheme.error)
                }
            },
            confirmButton = { TextButton(onClick = onClose) { Text("확인") } },
        )
    }
}

@Composable
private fun AppTheme(content: @Composable () -> Unit) {
    val blue = Color(0xFF1E6FFF)
    val scheme = if (isSystemInDarkTheme()) darkColorScheme(primary = Color(0xFF8AB4FF))
    else lightColorScheme(primary = blue)
    MaterialTheme(colorScheme = scheme, content = content)
}
