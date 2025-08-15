package com.imageflow.kmp.network.impl

import com.imageflow.kmp.network.*
import com.imageflow.kmp.workflow.ProductSearchQuery
import kotlinx.serialization.json.Json
import kotlinx.serialization.decodeFromString

class KtorProductApiService(
    private val rest: RestClient,
    private val json: Json = Json { ignoreUnknownKeys = true; isLenient = true }
) : ProductApiService {

    override suspend fun getProductInfo(productId: String): ApiResult<com.imageflow.kmp.models.ProductInfo> =
        runCatching {
            val body = rest.get("products/$productId")
            val product = json.decodeFromString<com.imageflow.kmp.models.ProductInfo>(body)
            ApiResult.Success(product)
        }.getOrElse { e -> networkError(e) }

    override suspend fun getProductByWorkOrderId(workOrderId: String): ApiResult<com.imageflow.kmp.models.ProductInfo> =
        runCatching {
            val path = "products/search?work_order_id=$workOrderId&limit=1"
            val body = rest.get(path)
            val resp = json.decodeFromString<ProductSearchResponse>(body)
            val first = resp.products.firstOrNull()
            if (first != null) ApiResult.Success(first)
            else ApiResult.Error("NOT_FOUND", "Product not found for work_order_id=$workOrderId")
        }.getOrElse { e -> networkError(e) }

    override suspend fun getProductByQrData(qrData: String): ApiResult<com.imageflow.kmp.models.ProductInfo> =
        runCatching {
            val path = "products/by-qr?data=${encode(qrData)}"
            val body = rest.get(path)
            val product = json.decodeFromString<com.imageflow.kmp.models.ProductInfo>(body)
            ApiResult.Success(product)
        }.getOrElse { e -> networkError(e) }

    override suspend fun searchProducts(query: ProductSearchQuery): ApiResult<ProductSearchResponse> =
        runCatching {
            val q = buildString {
                query.workOrderId?.let { append("work_order_id=$it&") }
                query.instructionId?.let { append("instruction_id=$it&") }
                query.productType?.let { append("product_type=${encode(it)}&") }
                query.machineNumber?.let { append("machine_number=${encode(it)}&") }
                query.productionDateRange?.let { append("start_date=${encode(it.startDate)}&end_date=${encode(it.endDate)}&") }
                append("limit=${query.limit}")
            }
            val body = rest.get("products/search?$q")
            val resp = json.decodeFromString<ProductSearchResponse>(body)
            ApiResult.Success(resp)
        }.getOrElse { e -> networkError(e) }

    override suspend fun getProductSuggestions(partialQuery: String): ApiResult<List<ProductSuggestion>> =
        runCatching {
            val body = rest.get("products/suggestions?q=${encode(partialQuery)}")
            val list = json.decodeFromString<List<ProductSuggestion>>(body)
            ApiResult.Success(list)
        }.getOrElse { e -> networkError(e) }

    override suspend fun getProductsByType(productType: String): ApiResult<List<com.imageflow.kmp.models.ProductInfo>> =
        runCatching {
            val body = rest.get("products?product_type=${encode(productType)}")
            val list = json.decodeFromString<List<com.imageflow.kmp.models.ProductInfo>>(body)
            ApiResult.Success(list)
        }.getOrElse { e -> networkError(e) }

    override suspend fun validateProduct(productInfo: com.imageflow.kmp.models.ProductInfo): ApiResult<ProductValidationResult> =
        ApiResult.Error("NOT_IMPLEMENTED", "Server-side validation endpoint not configured")

    override suspend fun validateQrCode(qrData: String): ApiResult<QrValidationResult> =
        ApiResult.Error("NOT_IMPLEMENTED", "Server-side QR validation endpoint not configured")

    override suspend fun getProductsBatch(productIds: List<String>): ApiResult<List<com.imageflow.kmp.models.ProductInfo>> =
        runCatching {
            val ids = productIds.joinToString(",") { encode(it) }
            val body = rest.get("products/batch?ids=$ids")
            val list = json.decodeFromString<List<com.imageflow.kmp.models.ProductInfo>>(body)
            ApiResult.Success(list)
        }.getOrElse { e -> networkError(e) }

    override suspend fun syncProductCache(lastSyncTime: Long): ApiResult<ProductSyncResponse> =
        runCatching {
            val body = rest.get("products/sync?last_sync=$lastSyncTime")
            val resp = json.decodeFromString<ProductSyncResponse>(body)
            ApiResult.Success(resp)
        }.getOrElse { e -> networkError(e) }

    private fun networkError(e: Throwable): ApiResult.NetworkError =
        ApiResult.NetworkError(e.message ?: "Network error")

    private fun encode(v: String): String = v
}
