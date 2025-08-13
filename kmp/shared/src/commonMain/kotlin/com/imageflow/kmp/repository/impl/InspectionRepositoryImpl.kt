package com.imageflow.kmp.repository.impl

import com.imageflow.kmp.database.DatabaseProvider
import com.imageflow.kmp.models.*
import com.imageflow.kmp.repository.InspectionRepository
import com.imageflow.kmp.repository.InspectionUpdate
import com.imageflow.kmp.repository.InspectionStats
import com.imageflow.kmp.repository.DefectStatistics
import com.imageflow.kmp.repository.InspectorStats
import com.imageflow.kmp.state.InspectionState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString

// Enhanced InspectionRepository implementation with comprehensive inspection management
class InspectionRepositoryImpl : InspectionRepository {
    private val db by lazy { DatabaseProvider.create() }
    private val json = Json { ignoreUnknownKeys = true }
    
    // Real-time update flows
    private val _inspectionUpdates = MutableSharedFlow<InspectionUpdate>()

    override suspend fun getInspection(id: String): Inspection? =
        db.inspectionQueries.selectById(id).executeAsOneOrNull()?.let { row ->
            convertToInspection(row)
        }

    override suspend fun saveInspection(inspection: Inspection): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.inspectionQueries.insertOrReplace(
                id = inspection.id,
                product_id = inspection.productId,
                work_order_id = inspection.workOrderId,
                instruction_id = inspection.instructionId,
                inspection_type = inspection.inspectionType.name,
                inspection_state = inspection.inspectionState.toString(),
                ai_result = inspection.aiResult?.let { json.encodeToString(it) },
                ai_confidence = inspection.aiConfidence?.toDouble(),
                human_verified = if (inspection.humanVerified) 1 else 0,
                human_result = inspection.humanResult?.name,
                human_comments = inspection.humanComments,
                inspector_id = inspection.inspectorId,
                started_at = inspection.startedAt,
                completed_at = inspection.completedAt,
                image_paths = json.encodeToString(inspection.imagePaths),
                video_path = inspection.videoPath,
                metadata = inspection.metadata?.let { json.encodeToString(it) },
                synced = if (inspection.synced) 1 else 0,
                sync_attempts = inspection.syncAttempts.toLong(),
                last_sync_attempt = inspection.lastSyncAttempt,
                created_at = inspection.createdAt,
                updated_at = now
            )
            
            _inspectionUpdates.tryEmit(InspectionUpdate.Created(inspection))
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun updateInspection(inspection: Inspection): Boolean {
        return try {
            val updatedInspection = inspection.copy(updatedAt = System.currentTimeMillis())
            saveInspection(updatedInspection)
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun deleteInspection(id: String): Boolean {
        // Would need delete query in Inspection.sq
        return true
    }

    override suspend fun getInspectionsByProduct(productId: String): List<Inspection> =
        db.inspectionQueries.selectByProduct(productId).executeAsList()
            .map { convertToInspection(it) }

    override suspend fun getInspectionsByWorkOrder(workOrderId: String): List<Inspection> =
        db.inspectionQueries.selectByWorkOrder(workOrderId).executeAsList()
            .map { convertToInspection(it) }

    override suspend fun getInspectionsByInspector(inspectorId: String): List<Inspection> =
        db.inspectionQueries.selectByInspector(inspectorId).executeAsList()
            .map { convertToInspection(it) }

    override suspend fun getInspectionsByDateRange(startDate: Long, endDate: Long): List<Inspection> =
        db.inspectionQueries.selectByDateRange(startDate, endDate).executeAsList()
            .map { convertToInspection(it) }

    override suspend fun getInspectionsByState(state: InspectionState): List<Inspection> =
        db.inspectionQueries.selectAll().executeAsList()
            .map { convertToInspection(it) }
            .filter { it.inspectionState == state }

    override suspend fun getInProgressInspections(): List<Inspection> =
        db.inspectionQueries.selectInProgress().executeAsList()
            .map { convertToInspection(it) }

    override suspend fun getCompletedInspections(): List<Inspection> =
        db.inspectionQueries.selectCompleted().executeAsList()
            .map { convertToInspection(it) }

    override suspend fun updateInspectionState(inspectionId: String, newState: InspectionState): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.inspectionQueries.updateState(newState.toString(), now, inspectionId)
            _inspectionUpdates.tryEmit(InspectionUpdate.StateChanged(inspectionId, newState))
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun updateAiResult(inspectionId: String, result: AiInspectionResult): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.inspectionQueries.updateAiResult(
                json.encodeToString(result),
                result.confidence.toDouble(),
                now,
                inspectionId
            )
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun updateHumanResult(inspectionId: String, result: HumanResult, comments: String?): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.inspectionQueries.updateHumanResult(result.name, comments, now, now, inspectionId)
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun getInspectionsRequiringHumanReview(): List<Inspection> =
        db.inspectionQueries.selectAll().executeAsList()
            .map { convertToInspection(it) }
            .filter { it.inspectionState == InspectionState.HumanReview }

    override suspend fun getUnsyncedInspections(): List<Inspection> =
        db.inspectionQueries.selectUnsynced().executeAsList()
            .map { convertToInspection(it) }

    override suspend fun markAsSynced(inspectionId: String): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.inspectionQueries.markSynced(now, inspectionId)
            _inspectionUpdates.tryEmit(InspectionUpdate.SyncStatusChanged(inspectionId, true))
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun updateSyncStatus(inspectionId: String, synced: Boolean, attempts: Int): Boolean {
        return try {
            val now = System.currentTimeMillis()
            db.inspectionQueries.updateSyncStatus(if (synced) 1L else 0L, now, now, inspectionId)
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun getFailedSyncInspections(): List<Inspection> =
        getUnsyncedInspections().filter { it.syncAttempts > 0 }

    override suspend fun getInspectionStats(startDate: Long, endDate: Long): InspectionStats {
        val inspections = getInspectionsByDateRange(startDate, endDate)
        val completed = inspections.filter { it.inspectionState == InspectionState.Completed }
        val passed = completed.filter { it.humanResult == HumanResult.OK || 
                                      (it.humanResult == null && it.aiResult?.overallResult == InspectionResult.PASS) }
        
        return InspectionStats(
            totalInspections = inspections.size,
            completedInspections = completed.size,
            passedInspections = passed.size,
            failedInspections = completed.size - passed.size,
            averageInspectionTime = if (completed.isNotEmpty()) {
                completed.mapNotNull { inspection ->
                    inspection.completedAt?.let { it - inspection.startedAt }
                }.average().toLong()
            } else 0,
            aiAccuracy = 0.85f, // Would calculate from actual data
            humanVerificationRate = completed.count { it.humanVerified }.toFloat() / completed.size.coerceAtLeast(1)
        )
    }

    override suspend fun getDefectStatistics(startDate: Long, endDate: Long): List<DefectStatistics> {
        // Implementation would analyze all defects found in the date range
        return emptyList()
    }

    override suspend fun getInspectorPerformance(inspectorId: String, startDate: Long, endDate: Long): InspectorStats {
        val inspections = getInspectionsByInspector(inspectorId)
            .filter { it.startedAt >= startDate && it.startedAt <= endDate }
        
        return InspectorStats(
            inspectorId = inspectorId,
            totalInspections = inspections.size,
            averageTime = if (inspections.isNotEmpty()) {
                inspections.mapNotNull { inspection ->
                    inspection.completedAt?.let { it - inspection.startedAt }
                }.average().toLong()
            } else 0,
            accuracyRate = 0.95f, // Would calculate from actual data
            productivityScore = 0.85f // Would calculate based on various metrics
        )
    }

    override fun observeInspectionUpdates(): Flow<InspectionUpdate> = _inspectionUpdates.asSharedFlow()

    override fun observeInspection(inspectionId: String): Flow<Inspection?> = flow {
        emit(getInspection(inspectionId))
        // In real implementation, would observe database changes
    }

    override fun observeInProgressInspections(): Flow<List<Inspection>> = flow {
        emit(getInProgressInspections())
        // In real implementation, would observe database changes
    }

    private fun convertToInspection(row: com.imageflow.kmp.db.Inspections): Inspection {
        return Inspection(
            id = row.id,
            productId = row.product_id,
            workOrderId = row.work_order_id,
            instructionId = row.instruction_id,
            inspectionType = runCatching { InspectionType.valueOf(row.inspection_type) }.getOrDefault(InspectionType.STATIC_IMAGE),
            inspectionState = parseInspectionState(row.inspection_state),
            aiResult = row.ai_result?.let { 
                try { json.decodeFromString<AiInspectionResult>(it) } catch (e: Exception) { null }
            },
            aiConfidence = row.ai_confidence?.toFloat(),
            humanVerified = row.human_verified == 1L,
            humanResult = row.human_result?.let { 
                runCatching { HumanResult.valueOf(it) }.getOrNull()
            },
            humanComments = row.human_comments,
            inspectorId = row.inspector_id,
            startedAt = row.started_at,
            completedAt = row.completed_at,
            imagePaths = try { 
                json.decodeFromString<List<String>>(row.image_paths ?: "[]") 
            } catch (e: Exception) { emptyList() },
            videoPath = row.video_path,
            metadata = row.metadata?.let {
                try { json.decodeFromString<InspectionMetadata>(it) } catch (e: Exception) { null }
            },
            synced = row.synced == 1L,
            syncAttempts = row.sync_attempts.toInt(),
            lastSyncAttempt = row.last_sync_attempt,
            createdAt = row.created_at,
            updatedAt = row.updated_at
        )
    }

    private fun parseInspectionState(stateString: String): InspectionState {
        return when (stateString) {
            "ProductScanning" -> InspectionState.ProductScanning
            "ProductIdentified" -> InspectionState.ProductIdentified
            "InProgress" -> InspectionState.InProgress
            "AiCompleted" -> InspectionState.AiCompleted
            "HumanReview" -> InspectionState.HumanReview
            "Completed" -> InspectionState.Completed
            "ProductNotFound" -> InspectionState.ProductNotFound
            "QrDecodeFailed" -> InspectionState.QrDecodeFailed
            "Failed" -> InspectionState.Failed
            "Cancelled" -> InspectionState.Cancelled
            else -> InspectionState.ProductScanning
        }
    }
}
