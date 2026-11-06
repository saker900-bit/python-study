package com.saker900.onetouchcleaner

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import com.android.billingclient.api.acknowledgePurchase
import com.android.billingclient.api.queryProductDetails
import com.android.billingclient.api.queryPurchasesAsync
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/**
 * 평생 광고 제거 (1회 구매, 소모되지 않는 상품).
 * Play Console > 수익 창출 > 인앱 상품 에서 ID [PRODUCT_ID], 가격 ₩5,900 으로 등록.
 */
class BillingManager(
    context: Context,
    private val prefs: Prefs,
    private val scope: CoroutineScope,
) : PurchasesUpdatedListener {

    private val _premium = MutableStateFlow(prefs.premium)
    val premium: StateFlow<Boolean> = _premium

    private val _price = MutableStateFlow<String?>(null)
    val price: StateFlow<String?> = _price

    private var details: ProductDetails? = null

    private val client = BillingClient.newBuilder(context)
        .setListener(this)
        .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
        .build()

    fun connect() {
        if (client.isReady) return
        client.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    scope.launch {
                        queryProduct()
                        restore()
                    }
                }
            }

            override fun onBillingServiceDisconnected() = Unit
        })
    }

    private suspend fun queryProduct() {
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(
                listOf(
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(PRODUCT_ID)
                        .setProductType(BillingClient.ProductType.INAPP)
                        .build()
                )
            ).build()
        val res = client.queryProductDetails(params)
        details = res.productDetailsList?.firstOrNull()
        _price.value = details?.oneTimePurchaseOfferDetails?.formattedPrice
    }

    /** 재설치/기기 변경 시 구매 복원, 환불 시 해제. */
    suspend fun restore() {
        if (!client.isReady) return
        val res = client.queryPurchasesAsync(
            QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build()
        )
        if (res.billingResult.responseCode != BillingClient.BillingResponseCode.OK) return
        val owned = res.purchasesList.filter {
            PRODUCT_ID in it.products && it.purchaseState == Purchase.PurchaseState.PURCHASED
        }
        owned.forEach { acknowledge(it) }
        setPremium(owned.isNotEmpty())
    }

    /** @return false 이면 상품 정보를 아직 못 가져온 상태 */
    fun buy(activity: Activity): Boolean {
        val d = details ?: run {
            connect()
            return false
        }
        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(
                listOf(BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(d).build())
            ).build()
        client.launchBillingFlow(activity, params)
        return true
    }

    override fun onPurchasesUpdated(result: BillingResult, purchases: MutableList<Purchase>?) {
        when (result.responseCode) {
            BillingClient.BillingResponseCode.OK -> scope.launch {
                purchases.orEmpty()
                    .filter { PRODUCT_ID in it.products && it.purchaseState == Purchase.PurchaseState.PURCHASED }
                    .forEach {
                        acknowledge(it)
                        setPremium(true)
                    }
            }
            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> scope.launch { restore() }
            else -> Unit
        }
    }

    private suspend fun acknowledge(p: Purchase) {
        if (p.isAcknowledged) return
        client.acknowledgePurchase(
            AcknowledgePurchaseParams.newBuilder().setPurchaseToken(p.purchaseToken).build()
        )
    }

    private fun setPremium(v: Boolean) {
        prefs.premium = v
        _premium.value = v
    }

    companion object {
        const val PRODUCT_ID = "remove_ads_lifetime"
    }
}
