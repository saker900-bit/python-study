package com.saker900.momradar

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.widget.Button
import android.widget.EditText
import android.widget.SeekBar
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {

    private lateinit var prefs: Prefs
    private lateinit var statusText: TextView
    private lateinit var liveText: TextView
    private lateinit var toggleButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = Prefs(this)
        Alerts.createChannels(this)

        statusText = findViewById(R.id.statusText)
        liveText = findViewById(R.id.liveText)
        toggleButton = findViewById(R.id.toggleButton)

        toggleButton.setOnClickListener {
            if (DetectorService.isRunning) stopDetector() else startWithPermissions()
        }

        bindSwitch(R.id.micSwitch, prefs.micEnabled) { prefs.micEnabled = it }
        bindSwitch(R.id.vibSwitch, prefs.vibEnabled) { prefs.vibEnabled = it }
        bindSwitch(R.id.approachSwitch, prefs.approachOnly) { prefs.approachOnly = it }

        bindSeek(R.id.micSens, R.id.micSensLabel, prefs.micSensitivity, 1, "발소리 감도") { prefs.micSensitivity = it }
        bindSeek(R.id.vibSens, R.id.vibSensLabel, prefs.vibSensitivity, 1, "진동 감도") { prefs.vibSensitivity = it }
        bindSeek(R.id.stepsSeek, R.id.stepsLabel, prefs.stepsNeeded, 2, "몇 걸음 들리면 알림") { prefs.stepsNeeded = it }

        val msg = findViewById<EditText>(R.id.messageEdit)
        msg.setText(prefs.alertMessage)
        msg.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) { prefs.alertMessage = s?.toString() ?: "" }
        })

        findViewById<Button>(R.id.testButton).setOnClickListener {
            ensureNotificationPermission()
            Alerts.fire(this, prefs.alertMessage, "테스트")
        }
    }

    override fun onResume() {
        super.onResume()
        DetectorService.statusListener = { s -> showStatus(s) }
        showStatus(null)
    }

    override fun onPause() {
        DetectorService.statusListener = null
        super.onPause()
    }

    // ---------- 시작 / 정지 ----------

    private fun startWithPermissions() {
        val needed = mutableListOf<String>()
        if (!has(Manifest.permission.RECORD_AUDIO)) needed += Manifest.permission.RECORD_AUDIO
        if (Build.VERSION.SDK_INT >= 33 && !has(Manifest.permission.POST_NOTIFICATIONS)) {
            needed += Manifest.permission.POST_NOTIFICATIONS
        }
        if (needed.isEmpty()) startDetector() else requestPermissions(needed.toTypedArray(), REQ_START)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQ_START) return
        if (!has(Manifest.permission.RECORD_AUDIO)) {
            Toast.makeText(this, "마이크 권한이 있어야 레이더를 켤 수 있어요", Toast.LENGTH_LONG).show()
            return
        }
        if (Build.VERSION.SDK_INT >= 33 && !has(Manifest.permission.POST_NOTIFICATIONS)) {
            Toast.makeText(this, "알림 권한이 없으면 진동으로만 알려드려요", Toast.LENGTH_LONG).show()
        }
        startDetector()
    }

    private fun startDetector() {
        if (!prefs.micEnabled && !prefs.vibEnabled) {
            Toast.makeText(this, "발소리나 진동 감지 중 하나는 켜 주세요", Toast.LENGTH_SHORT).show()
            return
        }
        startForegroundService(Intent(this, DetectorService::class.java))
        statusText.text = "켜는 중…"
        toggleButton.postDelayed({ showStatus(null) }, 400)
    }

    private fun stopDetector() {
        stopService(Intent(this, DetectorService::class.java))
        toggleButton.postDelayed({ showStatus(null) }, 200)
    }

    private fun ensureNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 && !has(Manifest.permission.POST_NOTIFICATIONS)) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIF)
        }
    }

    private fun has(p: String) = checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED

    // ---------- 화면 표시 ----------

    private fun showStatus(s: DetectorService.LiveStatus?) {
        val running = DetectorService.isRunning
        toggleButton.text = if (running) "감시 끄기" else "감시 시작"
        if (!running) {
            statusText.text = "⚪ 꺼져 있음"
            liveText.text = "시작하면 백그라운드에서 계속 감시해요.\n다른 앱(게임, 유튜브)을 켜도 돼요."
            return
        }
        statusText.text = "🟢 감시 중"
        if (s == null) return
        val sb = StringBuilder()
        if (s.micOn) {
            sb.append("🎤 소리  %5.1f dB (기준 %5.1f)  걸음 %d\n".format(s.micDb, s.micFloorDb, s.micSteps))
        } else if (prefs.micEnabled) {
            sb.append("🎤 마이크를 열 수 없음 (다른 앱이 사용 중?)\n")
        }
        if (s.vibOn) {
            if (s.handling) {
                sb.append("📳 진동  폰을 들고 있어서 쉬는 중\n")
            } else {
                sb.append("📳 진동  %.3f (기준 %.3f)  걸음 %d\n".format(s.vibPeak, s.vibFloor, s.vibSteps))
            }
        }
        s.lastAlertAgoSec?.let { sb.append("🚨 마지막 알림: ${it}초 전") }
        liveText.text = sb.toString().trimEnd()
    }

    // ---------- 설정 바인딩 ----------

    private fun bindSwitch(id: Int, value: Boolean, onChange: (Boolean) -> Unit) {
        val sw = findViewById<Switch>(id)
        sw.isChecked = value
        sw.setOnCheckedChangeListener { _, checked -> onChange(checked) }
    }

    private fun bindSeek(id: Int, labelId: Int, value: Int, min: Int, title: String, onChange: (Int) -> Unit) {
        val seek = findViewById<SeekBar>(id)
        val label = findViewById<TextView>(labelId)
        val suffix = if (title.contains("걸음")) "걸음" else " / 10"
        label.text = "$title: $value$suffix"
        seek.progress = value - min
        seek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                label.text = "$title: ${progress + min}$suffix"
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {
                onChange((sb?.progress ?: 0) + min)
            }
        })
    }

    companion object {
        private const val REQ_START = 10
        private const val REQ_NOTIF = 11
    }
}
