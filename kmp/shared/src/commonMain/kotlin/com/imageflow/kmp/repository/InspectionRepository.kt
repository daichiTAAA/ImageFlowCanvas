package com.imageflow.kmp.repository

import com.imageflow.kmp.models.*
import com.imageflow.kmp.state.InspectionState
import kotlinx.coroutines.flow.Flow

// Enhanced Inspection Repository interface based on F-022, F-023, F-024 requirements
interface InspectionRepository {
    // Basic inspection operations
    suspend fun getInspection(id: String): Inspection?
    suspend fun saveInspection(inspection: Inspection): Boolean
    suspend fun updateInspection(inspection: Inspection): Boolean
    suspend fun deleteInspection(id: String): Boolean
    
    // Query operations
    suspend fun getInspectionsByProduct(productId: String): List<Inspection>
    suspend fun getInspectionsByWorkOrder(workOrderId: String): List<Inspection>
    suspend fun getInspectionsByInspector(inspectorId: String): List<Inspection>
    suspend fun getInspectionsByDateRange(startDate: Long, endDate: Long): List<Inspection>
    suspend fun getInspectionsByState(state: InspectionState): List<Inspection>
    
    // State and progress tracking
    suspend fun getInProgressInspections(): List<Inspection>
    suspend fun getCompletedInspections(): List<Inspection>
    suspend fun updateInspectionState(inspectionId: String, newState: InspectionState): Boolean
    
    // AI and human verification
    suspend fun updateAiResult(inspectionId: String, result: AiInspectionResult): Boolean
    suspend fun updateHumanResult(inspectionId: String, result: HumanResult, comments: String?): Boolean
    suspend fun getInspectionsRequiringHumanReview(): List<Inspection>
    
    // Sync operations
    suspend fun getUnsyncedInspections(): List<Inspection>
    suspend fun markAsSynced(inspectionId: String): Boolean
    suspend fun updateSyncStatus(inspectionId: String, synced: Boolean, attempts: Int): Boolean
    suspend fun getFailedSyncInspections(): List<Inspection>
    
    // Statistics and reporting
    suspend fun getInspectionStats(startDate: Long, endDate: Long): InspectionStats
    suspend fun getDefectStatistics(startDate: Long, endDate: Long): List<DefectStatistics>
    suspend fun getInspectorPerformance(inspectorId: String, startDate: Long, endDate: Long): InspectorStats
    
    // Real-time updates
    fun observeInspectionUpdates(): Flow<InspectionUpdate>
    fun observeInspection(inspectionId: String): Flow<Inspection?>
    fun observeInProgressInspections(): Flow<List<Inspection>>
}

data class InspectionStats(
    val totalInspections: Int,
    val completedInspections: Int,
    val passedInspections: Int,
    val failedInspections: Int,
    val averageInspectionTime: Long,
    val aiAccuracy: Float,
    val humanVerificationRate: Float
)

data class DefectStatistics(
    val defectType: DefectType,
    val count: Int,
    val severity: DefectSeverity,
    val averageConfidence: Float
)

data class InspectorStats(
    val inspectorId: String,
    val totalInspections: Int,
    val averageTime: Long,
    val accuracyRate: Float,
    val productivityScore: Float
)

sealed class InspectionUpdate {
    data class Created(val inspection: Inspection) : InspectionUpdate()
    data class StateChanged(val inspectionId: String, val newState: InspectionState) : InspectionUpdate()
    data class Completed(val inspection: Inspection) : InspectionUpdate()
    data class SyncStatusChanged(val inspectionId: String, val synced: Boolean) : InspectionUpdate()
}

