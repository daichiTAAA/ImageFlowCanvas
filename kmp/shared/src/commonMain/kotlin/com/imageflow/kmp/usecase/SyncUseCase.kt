package com.imageflow.kmp.usecase

import com.imageflow.kmp.models.*
import com.imageflow.kmp.repository.InspectionRepository
import com.imageflow.kmp.network.InspectionApiService
import com.imageflow.kmp.network.ApiResult
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

// Use case for data synchronization and offline support
class SyncUseCase(
    private val inspectionRepository: InspectionRepository,
    private val inspectionApiService: InspectionApiService
) {
    
    suspend fun syncInspections(): SyncResult {
        return try {
            val unsyncedInspections = inspectionRepository.getUnsyncedInspections()
            var successCount = 0
            var failedCount = 0
            val errors = mutableMapOf<String, String>()
            
            // Submit unsynced inspections
            unsyncedInspections.forEach { inspection ->
                try {
                    val submission = InspectionSubmission(
                        inspectionId = inspection.id,
                        finalResult = when (inspection.humanResult) {
                            HumanResult.OK -> InspectionResult.PASS
                            HumanResult.NG -> InspectionResult.FAIL
                            HumanResult.PENDING -> InspectionResult.PENDING
                            null -> InspectionResult.PENDING
                        },
                        humanVerified = inspection.humanVerified,
                        humanComments = inspection.humanComments
                    )
                    
                    when (val result = inspectionApiService.submitInspectionResult(inspection.id, submission)) {
                        is ApiResult.Success -> {
                            inspectionRepository.markAsSynced(inspection.id)
                            successCount++
                        }
                        is ApiResult.Error -> {
                            inspectionRepository.updateSyncStatus(inspection.id, false, inspection.syncAttempts + 1)
                            errors[inspection.id] = result.message
                            failedCount++
                        }
                        is ApiResult.NetworkError -> {
                            errors[inspection.id] = result.message
                            failedCount++
                        }
                    }
                } catch (e: Exception) {
                    errors[inspection.id] = e.message ?: "Unknown error"
                    failedCount++
                }
            }
            
            SyncResult(
                totalInspections = unsyncedInspections.size,
                successfulSyncs = successCount,
                failedSyncs = failedCount,
                errors = errors,
                syncTimestamp = System.currentTimeMillis()
            )
        } catch (e: Exception) {
            SyncResult(
                totalInspections = 0,
                successfulSyncs = 0,
                failedSyncs = 0,
                errors = mapOf("sync_error" to (e.message ?: "Sync failed")),
                syncTimestamp = System.currentTimeMillis()
            )
        }
    }
    
    suspend fun downloadLatestData(): SyncResult {
        return try {
            when (val result = inspectionApiService.syncInspectionData(0)) {
                is ApiResult.Success -> {
                    val syncResponse = result.data
                    var successCount = 0
                    
                    // Update local inspections with server data
                    syncResponse.updates.forEach { inspection ->
                        try {
                            inspectionRepository.updateInspection(inspection)
                            successCount++
                        } catch (e: Exception) {
                            // Log error but continue
                        }
                    }
                    
                    SyncResult(
                        totalInspections = syncResponse.updates.size,
                        successfulSyncs = successCount,
                        failedSyncs = syncResponse.updates.size - successCount,
                        errors = emptyMap(),
                        syncTimestamp = syncResponse.syncTimestamp
                    )
                }
                is ApiResult.Error -> {
                    SyncResult(
                        totalInspections = 0,
                        successfulSyncs = 0,
                        failedSyncs = 0,
                        errors = mapOf("download_error" to result.message),
                        syncTimestamp = System.currentTimeMillis()
                    )
                }
                is ApiResult.NetworkError -> {
                    SyncResult(
                        totalInspections = 0,
                        successfulSyncs = 0,
                        failedSyncs = 0,
                        errors = mapOf("network_error" to result.message),
                        syncTimestamp = System.currentTimeMillis()
                    )
                }
            }
        } catch (e: Exception) {
            SyncResult(
                totalInspections = 0,
                successfulSyncs = 0,
                failedSyncs = 0,
                errors = mapOf("download_error" to (e.message ?: "Download failed")),
                syncTimestamp = System.currentTimeMillis()
            )
        }
    }
    
    fun observeSyncStatus(): Flow<SyncStatus> = flow {
        // Implementation would observe actual sync operations
        emit(SyncStatus.SYNCED)
    }
}

data class SyncResult(
    val totalInspections: Int,
    val successfulSyncs: Int,
    val failedSyncs: Int,
    val errors: Map<String, String>,
    val syncTimestamp: Long
) {
    val isSuccessful: Boolean
        get() = failedSyncs == 0 && totalInspections > 0
    
    val hasErrors: Boolean
        get() = errors.isNotEmpty()
}