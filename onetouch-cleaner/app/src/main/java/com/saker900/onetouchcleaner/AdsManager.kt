package com.saker900.onetouchcleaner

import android.app.Activity
import android.content.Context
import com.google.android.gms.ads.AdError
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.FullScreenContentCallback
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.rewarded.RewardedAd
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback
import com.google.android.ump.ConsentRequestParameters
import com.google.android.ump.UserMessagingPlatform

/** 보상형 광고: 끝까지 보면 정리 실행. */
object AdsManager {
    private var ad: RewardedAd? = null
    private var loading = false

    /** 동의(GDPR 등) 확인 후 광고 미리 로드. */
    fun init(activity: Activity) {
        val info = UserMessagingPlatform.getConsentInformation(activity)
        info.requestConsentInfoUpdate(
            activity,
            ConsentRequestParameters.Builder().build(),
            {
                UserMessagingPlatform.loadAndShowConsentFormIfRequired(activity) {
                    if (info.canRequestAds()) preload(activity)
                }
            },
            { preload(activity) },
        )
    }

    fun preload(context: Context) {
        if (ad != null || loading) return
        loading = true
        RewardedAd.load(
            context.applicationContext,
            BuildConfig.REWARDED_AD_UNIT_ID,
            AdRequest.Builder().build(),
            object : RewardedAdLoadCallback() {
                override fun onAdLoaded(loaded: RewardedAd) {
                    ad = loaded
                    loading = false
                }

                override fun onAdFailedToLoad(error: LoadAdError) {
                    loading = false
                }
            },
        )
    }

    /**
     * 광고를 보여주고, 보상 획득 후 광고가 닫히면 [onRewarded].
     * 광고를 불러오지 못했으면 [onUnavailable] (사용자를 막지 않기 위해 그냥 실행하도록 처리).
     */
    fun show(activity: Activity, onRewarded: () -> Unit, onUnavailable: () -> Unit) {
        val current = ad ?: run {
            preload(activity)
            onUnavailable()
            return
        }
        ad = null
        var earned = false
        current.fullScreenContentCallback = object : FullScreenContentCallback() {
            override fun onAdDismissedFullScreenContent() {
                preload(activity)
                if (earned) onRewarded()
            }

            override fun onAdFailedToShowFullScreenContent(error: AdError) {
                preload(activity)
                onUnavailable()
            }
        }
        current.show(activity) { earned = true }
    }
}
