package com.saker900.onetouchcleaner

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = (app as CleanerApp).prefs

    private val _apps = MutableStateFlow<List<AppItem>>(emptyList())
    val apps: StateFlow<List<AppItem>> = _apps

    private val _loading = MutableStateFlow(true)
    val loading: StateFlow<Boolean> = _loading

    private val _selected = MutableStateFlow<Set<String>>(emptySet())
    val selected: StateFlow<Set<String>> = _selected

    private val _clearCache = MutableStateFlow(prefs.clearCache)
    val clearCache: StateFlow<Boolean> = _clearCache

    init { reload() }

    fun reload() {
        viewModelScope.launch {
            _apps.value = AppRepository.loadApps(getApplication())
            recompute()
            _loading.value = false
        }
    }

    fun setClearCache(v: Boolean) {
        prefs.clearCache = v
        _clearCache.value = v
    }

    fun toggle(app: AppItem, checked: Boolean) = setChecked(listOf(app), checked)

    fun setChecked(apps: List<AppItem>, checked: Boolean) {
        val (system, user) = apps.partition { it.isSystem }
        val sysPkgs = system.map { it.packageName }.toSet()
        val userPkgs = user.map { it.packageName }.toSet()
        prefs.included = if (checked) prefs.included + sysPkgs else prefs.included - sysPkgs
        prefs.excluded = if (checked) prefs.excluded - userPkgs else prefs.excluded + userPkgs
        recompute()
    }

    fun targets(): List<CleanTarget> =
        _apps.value.filter { it.packageName in _selected.value }.map { CleanTarget(it.packageName, it.label) }

    private fun recompute() {
        _selected.value = _apps.value.filter { AppRepository.isSelected(it, prefs) }.map { it.packageName }.toSet()
    }
}
