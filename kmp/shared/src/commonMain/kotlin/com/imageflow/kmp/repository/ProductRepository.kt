package com.imageflow.kmp.repository

import com.imageflow.kmp.models.*
import com.imageflow.kmp.workflow.ProductSearchQuery
import kotlinx.coroutines.flow.Flow

// Enhanced Product Repository interface based on F-021-1, F-021-2 requirements
interface ProductRepository {
    // Basic product operations
    suspend fun getProduct(id: String): ProductInfo?
    suspend fun getProductByWorkOrderId(workOrderId: String): ProductInfo?
    suspend fun getProductByQrData(qrData: String): ProductInfo?
    
    // Search operations
    suspend fun searchProducts(query: ProductSearchQuery): List<ProductInfo>
    suspend fun getFrequentlyUsedProducts(limit: Int = 100): List<ProductInfo>
    suspend fun getRecentProducts(limit: Int = 50): List<ProductInfo>
    suspend fun getProductsByCode(productCode: String): List<ProductInfo>
    
    // CRUD operations
    suspend fun saveProduct(product: ProductInfo): Boolean
    suspend fun updateProduct(product: ProductInfo): Boolean
    suspend fun deleteProduct(id: String): Boolean
    
    // Access tracking for smart caching
    suspend fun updateAccessInfo(productId: String)
    suspend fun getAccessStatistics(productId: String): ProductAccessStats?
    
    // Offline/sync operations
    suspend fun getCachedProducts(): List<ProductInfo>
    suspend fun getUnsyncedProducts(): List<ProductInfo>
    suspend fun markAsSynced(productId: String): Boolean
    suspend fun updateSyncStatus(productId: String, status: SyncStatus): Boolean
    
    // Cache management
    suspend fun clearOldCache(olderThanDays: Int = 30): Int
    suspend fun preloadFrequentProducts(): Boolean
    
    // Real-time updates
    fun observeProductUpdates(): Flow<ProductUpdate>
    fun observeProduct(productId: String): Flow<ProductInfo?>
}

data class ProductAccessStats(
    val productId: String,
    val accessCount: Int,
    val lastAccessedAt: Long,
    val averageAccessInterval: Long,
    val totalUsageTime: Long
)

sealed class ProductUpdate {
    data class Added(val product: ProductInfo) : ProductUpdate()
    data class Modified(val product: ProductInfo) : ProductUpdate()
    data class Deleted(val productId: String) : ProductUpdate()
    data class SyncStatusChanged(val productId: String, val status: SyncStatus) : ProductUpdate()
}
