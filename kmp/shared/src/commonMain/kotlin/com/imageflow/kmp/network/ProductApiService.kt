package com.imageflow.kmp.network

import com.imageflow.kmp.models.*
import com.imageflow.kmp.qr.DecodedProductInfo
import com.imageflow.kmp.workflow.ProductSearchQuery
import kotlinx.serialization.Serializable

// Product API Service interface for backend communication
// Based on F-021-2 server information retrieval requirements
interface ProductApiService {
    // Product information retrieval
    suspend fun getProductInfo(productId: String): ApiResult<ProductInfo>
    suspend fun getProductByWorkOrderId(workOrderId: String): ApiResult<ProductInfo>
    suspend fun getProductByQrData(qrData: String): ApiResult<ProductInfo>
    
    // Product search and discovery
    suspend fun searchProducts(query: ProductSearchQuery): ApiResult<ProductSearchResponse>
    suspend fun getProductSuggestions(partialQuery: String): ApiResult<List<ProductSuggestion>>
    suspend fun getProductsByCode(productCode: String): ApiResult<List<ProductInfo>>
    
    // Product validation
    suspend fun validateProduct(productInfo: ProductInfo): ApiResult<ProductValidationResult>
    suspend fun validateQrCode(qrData: String): ApiResult<QrValidationResult>
    
    // Batch operations
    suspend fun getProductsBatch(productIds: List<String>): ApiResult<List<ProductInfo>>
    suspend fun syncProductCache(lastSyncTime: Long): ApiResult<ProductSyncResponse>
}

@Serializable
data class ProductSearchResponse(
    val products: List<ProductInfo>,
    val totalCount: Int,
    val hasMore: Boolean,
    val nextPageToken: String? = null
)

@Serializable
data class ProductSuggestion(
    val productId: String,
    val displayText: String,
    val productCode: String,
    val machineNumber: String,
    val relevanceScore: Float
)

@Serializable
data class ProductValidationResult(
    val isValid: Boolean,
    val exists: Boolean,
    val status: ProductStatus,
    val errors: List<String> = emptyList(),
    val warnings: List<String> = emptyList()
)

@Serializable
data class QrValidationResult(
    val isValid: Boolean,
    val productExists: Boolean,
    val decodedData: DecodedProductInfo?,
    val confidence: Float,
    val errors: List<String> = emptyList()
)

@Serializable
data class ProductSyncResponse(
    val updates: List<ProductInfo>,
    val deletions: List<String>,
    val syncTimestamp: Long,
    val totalUpdated: Int,
    val totalDeleted: Int
)

// Generic API result wrapper
@Serializable
sealed class ApiResult<out T> {
    @Serializable
    data class Success<T>(val data: T) : ApiResult<T>()
    
    @Serializable
    data class Error(
        val code: String,
        val message: String,
        val details: Map<String, String> = emptyMap()
    ) : ApiResult<Nothing>()
    
    @Serializable
    data class NetworkError(val message: String) : ApiResult<Nothing>()
}

// Extension functions for easier result handling
inline fun <T> ApiResult<T>.onSuccess(action: (T) -> Unit): ApiResult<T> {
    if (this is ApiResult.Success) action(data)
    return this
}

inline fun <T> ApiResult<T>.onError(action: (String) -> Unit): ApiResult<T> {
    when (this) {
        is ApiResult.Error -> action(message)
        is ApiResult.NetworkError -> action(message)
        else -> {}
    }
    return this
}

fun <T> ApiResult<T>.getOrNull(): T? = when (this) {
    is ApiResult.Success -> data
    else -> null
}

fun <T> ApiResult<T>.isSuccess(): Boolean = this is ApiResult.Success
fun <T> ApiResult<T>.isError(): Boolean = this !is ApiResult.Success
