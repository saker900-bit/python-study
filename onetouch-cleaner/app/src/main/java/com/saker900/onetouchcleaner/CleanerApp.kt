package com.saker900.onetouchcleaner

import android.app.Application
import com.google.android.gms.ads.MobileAds
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class CleanerApp : Application() {
    val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    lateinit var prefs: Prefs
        private set
    lateinit var billing: BillingManager
        private set

    override fun onCreate() {
        super.onCreate()
        prefs = Prefs(this)
        billing = BillingManager(this, prefs, appScope)
        billing.connect()
        if (!prefs.premium) {
            appScope.launch(Dispatchers.IO) { MobileAds.initialize(this@CleanerApp) {} }
        }
    }
}
