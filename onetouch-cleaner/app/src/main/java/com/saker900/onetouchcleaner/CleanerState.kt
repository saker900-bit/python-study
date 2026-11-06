package com.saker900.onetouchcleaner

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class CleanTarget(val packageName: String, val label: String)

data class CleanResult(
    val total: Int = 0,
    val stopped: Int = 0,
    val notRunning: Int = 0,
    val cacheCleared: Int = 0,
    val failed: Int = 0,
    val cancelled: Boolean = false,
)

sealed interface CleanStatus {
    data object Idle : CleanStatus
    data class Running(val index: Int, val total: Int, val label: String) : CleanStatus
    data class Done(val result: CleanResult) : CleanStatus
}

/** 접근성 서비스와 화면이 공유하는 진행 상태. */
object CleanerState {
    private val _status = MutableStateFlow<CleanStatus>(CleanStatus.Idle)
    val status: StateFlow<CleanStatus> = _status

    fun set(s: CleanStatus) { _status.value = s }
    fun reset() { _status.value = CleanStatus.Idle }
}
