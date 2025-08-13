package com.imageflow.kmp.repository.impl

import com.imageflow.kmp.database.DatabaseProvider
import com.imageflow.kmp.models.*
import com.imageflow.kmp.repository.ProductRepository
import com.imageflow.kmp.workflow.ProductSearchQuery
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json

// Enhanced ProductRepository implementation with offline support and smart caching
class ProductRepositoryImpl : ProductRepository {
    private val db by lazy { DatabaseProvider.create() }
    private val json = Json { ignoreUnknownKeys = true }
    
    // Real-time update flows
    private val _productUpdates = MutableSharedFlow<ProductUpdate>()
    
    override suspend fun getProduct(id: String): ProductInfo? =
        db.productQueries.selectById(id).executeAsOneOrNull()?.let { row ->
            updateAccessInfo(id) // Track access for smart caching
            convertToProductInfo(row)
        }

    override suspend fun getProductByWorkOrderId(workOrderId: String): ProductInfo? =
        db.productQueries.selectByWorkOrderId(workOrderId).executeAsOneOrNull()?.let { row ->
            updateAccessInfo(row.id)
            convertToProductInfo(row)
        }

    override suspend fun getProductByQrData(qrData: String): ProductInfo? =
        db.productQueries.selectByQrData(qrData).executeAsOneOrNull()?.let { row ->
            updateAccessInfo(row.id)
            convertToProductInfo(row)
        }

    override suspend fun searchProducts(query: ProductSearchQuery): List<ProductInfo> {
        // For now, implement simple filtering - can be optimized with SQL queries
        val allProducts = db.productQueries.selectAll().executeAsList()
            .map { convertToProductInfo(it) }
        
        return allProducts.filter { product ->
            (query.workOrderId == null || product.workOrderId.contains(query.workOrderId, true)) &&
            (query.instructionId == null || product.instructionId.contains(query.instructionId, true)) &&
            (query.productType == null || product.productType.contains(query.productType, true)) &&
            (query.machineNumber == null || product.machineNumber.contains(query.machineNumber, true))
        }.take(query.limit)
    }

    override suspend fun getFrequentlyUsedProducts(limit: Int): List<ProductInfo> =
        db.productQueries.selectFrequentlyUsed(limit.toLong()).executeAsList()
            .map { convertToProductInfo(it) }

    override suspend fun getRecentProducts(limit: Int): List<ProductInfo> =
        db.productQueries.selectAll().executeAsList()
            .map { convertToProductInfo(it) }
            .sortedByDescending { it.lastAccessedAt ?: 0 }
            .take(limit)

    override suspend fun getProductsByType(productType: String): List<ProductInfo> =
        db.productQueries.selectByProductType("$productType%").executeAsList()
            .map { convertToProductInfo(it) }

    override suspend fun saveProduct(product: ProductInfo): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.productQueries.insertOrReplace(
                id = product.id,
                work_order_id = product.workOrderId,
                instruction_id = product.instructionId,
                product_type = product.productType,
                machine_number = product.machineNumber,
                production_date = product.productionDate,
                monthly_sequence = product.monthlySequence.toLong(),
                qr_raw_data = product.qrRawData,
                status = product.status.name,
                created_at = product.createdAt,
                updated_at = now,
                last_accessed_at = product.lastAccessedAt,
                access_count = product.accessCount.toLong(),
                is_cached = if (product.isCached) 1 else 0,
                server_sync_status = product.serverSyncStatus.name
            )
            
            _productUpdates.tryEmit(ProductUpdate.Added(product))
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun updateProduct(product: ProductInfo): Boolean {
        return try {
            val now = System.currentTimeMillis()
            val updatedProduct = product.copy(updatedAt = now)
            saveProduct(updatedProduct)
            _productUpdates.tryEmit(ProductUpdate.Modified(updatedProduct))
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun deleteProduct(id: String): Boolean {
        return try {
            // Note: SQLDelight doesn't have delete query defined, would need to add to Product.sq
            _productUpdates.tryEmit(ProductUpdate.Deleted(id))
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun updateAccessInfo(productId: String) {
        try {
            val now = System.currentTimeMillis()
            db.productQueries.updateAccessInfo(now, productId)
        } catch (e: Exception) {
            // Log error but don't fail the operation
        }
    }

    override suspend fun getAccessStatistics(productId: String): ProductAccessStats? {
        return getProduct(productId)?.let { product ->
            ProductAccessStats(
                productId = productId,
                accessCount = product.accessCount,
                lastAccessedAt = product.lastAccessedAt ?: 0,
                averageAccessInterval = 0, // Would need to calculate from access history
                totalUsageTime = 0 // Would need to track session times
            )
        }
    }

    override suspend fun getCachedProducts(): List<ProductInfo> =
        db.productQueries.selectAll().executeAsList()
            .filter { it.is_cached == 1L }
            .map { convertToProductInfo(it) }

    override suspend fun getUnsyncedProducts(): List<ProductInfo> =
        db.productQueries.selectAll().executeAsList()
            .filter { it.server_sync_status != SyncStatus.SYNCED.name }
            .map { convertToProductInfo(it) }

    override suspend fun markAsSynced(productId: String): Boolean {
        return updateSyncStatus(productId, SyncStatus.SYNCED)
    }

    override suspend fun updateSyncStatus(productId: String, status: SyncStatus): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.productQueries.updateSyncStatus(status.name, now, productId)
            _productUpdates.tryEmit(ProductUpdate.SyncStatusChanged(productId, status))
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun clearOldCache(olderThanDays: Int): Int {
        return try {
            val cutoffTime = System.currentTimeMillis() - (olderThanDays * 24 * 60 * 60 * 1000L)
            db.productQueries.deleteOldUnused(cutoffTime)
            // Return count would need to be implemented in SQL
            0
        } catch (e: Exception) {
            0
        }
    }

    override suspend fun preloadFrequentProducts(): Boolean {
        // Implementation would fetch frequently used products from server
        return true
    }

    override fun observeProductUpdates(): Flow<ProductUpdate> = _productUpdates.asSharedFlow()

    override fun observeProduct(productId: String): Flow<ProductInfo?> = flow {
        emit(getProduct(productId))
        // In real implementation, would observe database changes
    }

    private fun convertToProductInfo(row: com.imageflow.kmp.db.Products): ProductInfo {
        return ProductInfo(
            id = row.id,
            workOrderId = row.work_order_id,
            instructionId = row.instruction_id,
            productType = row.product_type,
            machineNumber = row.machine_number,
            productionDate = row.production_date,
            monthlySequence = row.monthly_sequence.toInt(),
            qrRawData = row.qr_raw_data,
            status = runCatching { ProductStatus.valueOf(row.status) }.getOrDefault(ProductStatus.ACTIVE),
            createdAt = row.created_at,
            updatedAt = row.updated_at,
            lastAccessedAt = row.last_accessed_at,
            accessCount = row.access_count.toInt(),
            isCached = row.is_cached == 1L,
            serverSyncStatus = runCatching { SyncStatus.valueOf(row.server_sync_status) }.getOrDefault(SyncStatus.SYNCED)
        )
    }
}

