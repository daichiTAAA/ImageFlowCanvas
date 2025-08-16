package com.imageflow.kmp.models

import kotlinx.serialization.Serializable

// Canonical product info used across KMP, matching QR decode fields
// Enhanced based on F-021-1, F-021-2 requirements for product identification
@Serializable
data class ProductInfo(
    val id: String = "", // Generated unique ID
    val workOrderId: String,
    val instructionId: String,
    val productCode: String,
    val machineNumber: String,
    val productionDate: String, // ISO-8601 (YYYY-MM-DD)
    val monthlySequence: Int,
    val qrRawData: String? = null,
    val status: ProductStatus = ProductStatus.ACTIVE,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val lastAccessedAt: Long? = null,
    val accessCount: Int = 0,
    val isCached: Boolean = true,
    val serverSyncStatus: SyncStatus = SyncStatus.SYNCED
) {
    // Generate a unique identifier based on product key fields
    fun generateId(): String {
        return "${workOrderId}_${instructionId}_${machineNumber}_${monthlySequence}"
    }
}

// Product status enumeration based on requirements
@Serializable
enum class ProductStatus {
    ACTIVE,     // 検査対象として有効な製品
    INACTIVE,   // 一時的に検査対象外の製品
    OBSOLETE    // 廃止された製品
}

// Sync status for offline support
@Serializable
enum class SyncStatus {
    SYNCED,     // サーバーと同期済み
    PENDING,    // 同期待ち
    FAILED      // 同期失敗
}

// QR scan result wrapper
@Serializable
data class QrScanResult(
    val success: Boolean,
    val productInfo: ProductInfo?,
    val rawData: String,
    val scanType: ScanType,
    val confidence: Float,
    val validationStatus: ValidationStatus,
    val errorMessage: String? = null
)

@Serializable
enum class ScanType {
    QR_CODE,
    CODE128,
    DATA_MATRIX,
    PDF417
}

@Serializable
enum class ValidationStatus {
    VALID,
    INVALID,
    NETWORK_ERROR,
    NOT_FOUND
}
