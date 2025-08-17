package com.imageflow.kmp.network

import com.imageflow.kmp.models.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

// Inspection API Service interface for AI processing and inspection management
// Based on F-022, F-023, F-024 requirements
interface InspectionApiService {
    // AI inspection processing
    suspend fun submitForAiInspection(request: AiInspectionRequest): ApiResult<AiInspectionResult>
    suspend fun getAiInspectionStatus(requestId: String): ApiResult<AiInspectionStatus>
    suspend fun uploadInspectionImage(inspectionId: String, imagePath: String): ApiResult<FileUploadResult>
    suspend fun uploadInspectionVideo(inspectionId: String, videoPath: String): ApiResult<FileUploadResult>
    
    // Inspection management
    suspend fun createInspection(inspection: Inspection): ApiResult<Inspection>
    suspend fun updateInspection(inspection: Inspection): ApiResult<Inspection>
    suspend fun submitInspectionResult(inspectionId: String, result: InspectionSubmission): ApiResult<InspectionResponse>
    suspend fun getInspectionHistory(productId: String): ApiResult<List<Inspection>>
    
    // Human verification and review
    suspend fun submitHumanReview(review: HumanReviewSubmission): ApiResult<HumanReviewResponse>
    suspend fun getInspectionsForReview(inspectorId: String): ApiResult<List<Inspection>>
    suspend fun updateReviewStatus(inspectionId: String, status: String): ApiResult<Boolean>
    
    // Inspection analytics and reporting
    suspend fun getInspectionStatistics(request: StatisticsRequest): ApiResult<InspectionStatisticsResponse>
    suspend fun generateInspectionReport(request: ReportRequest): ApiResult<InspectionReport>
    
    // Real-time streaming (for THINKLET and live inspection)
    suspend fun startRealtimeInspection(request: RealtimeInspectionRequest): ApiResult<RealtimeSession>
    suspend fun stopRealtimeInspection(sessionId: String): ApiResult<Boolean>
    
    // Batch operations and sync
    suspend fun submitInspectionBatch(inspections: List<Inspection>): ApiResult<BatchSubmissionResult>
    suspend fun syncInspectionData(lastSyncTime: Long): ApiResult<InspectionSyncResponse>

    // Masters: fetch inspection items configured on Web for given product + process
    suspend fun getInspectionItemsForProduct(productId: String, processCode: String, page: Int = 1, pageSize: Int = 100): ApiResult<PaginatedResponse<InspectionItemKmp>>
}

@Serializable
data class PaginatedResponse<T>(
    val items: List<T>,
    val total_count: Int,
    val page: Int,
    val page_size: Int,
    val total_pages: Int
)

@Serializable
data class InspectionItemKmp(
    val id: String,
    val target_id: String,
    val name: String,
    val description: String? = null,
    val type: String,
    val pipeline_id: String? = null,
    val pipeline_params: Map<String, String>? = null,
    val execution_order: Int = 1,
    val is_required: Boolean = true,
    val criteria_id: String? = null
)

@Serializable
data class AiInspectionRequest(
    val inspectionId: String,
    val productId: String,
    val inspectionType: InspectionType,
    val imagePaths: List<String> = emptyList(),
    val videoPath: String? = null,
    val parameters: Map<String, String> = emptyMap(),
    val priority: AiProcessingPriority = AiProcessingPriority.NORMAL
)

@Serializable
enum class AiProcessingPriority {
    LOW, NORMAL, HIGH, URGENT
}

@Serializable
data class AiInspectionStatus(
    val requestId: String,
    val status: ProcessingStatus,
    val progress: Float,
    val estimatedTimeRemaining: Long? = null,
    val result: AiInspectionResult? = null,
    val error: String? = null
)

@Serializable
enum class ProcessingStatus {
    QUEUED, PROCESSING, COMPLETED, FAILED, CANCELLED
}

@Serializable
data class FileUploadResult(
    val fileId: String,
    val uploadedPath: String,
    val sizeBytes: Long,
    val checksum: String
)

@Serializable
data class InspectionSubmission(
    val inspectionId: String,
    val finalResult: InspectionResult,
    val humanVerified: Boolean,
    val humanComments: String? = null,
    val metadata: Map<String, String> = emptyMap()
)

@Serializable
data class InspectionResponse(
    val inspectionId: String,
    val accepted: Boolean,
    val traceabilityId: String,
    val timestamp: Long,
    val nextSteps: List<String> = emptyList()
)

@Serializable
data class HumanReviewSubmission(
    val inspectionId: String,
    val reviewerId: String,
    val overallResult: HumanResult,
    val defectReviews: List<DefectReviewSubmission> = emptyList(),
    val comments: String? = null,
    val reviewTimeMs: Long
)

@Serializable
data class DefectReviewSubmission(
    val defectId: String,
    val humanResult: HumanResult,
    val confidence: Float,
    val comments: String? = null
)

@Serializable
data class HumanReviewResponse(
    val accepted: Boolean,
    val updatedInspection: Inspection,
    val qualityScore: Float,
    val feedback: String? = null
)

@Serializable
data class StatisticsRequest(
    val startDate: Long,
    val endDate: Long,
    val productCodes: List<String> = emptyList(),
    val inspectorIds: List<String> = emptyList(),
    val groupBy: List<StatisticsGrouping> = emptyList()
)

@Serializable
enum class StatisticsGrouping {
    DATE, PRODUCT_CODE, INSPECTOR, DEFECT_TYPE, RESULT
}

@Serializable
data class InspectionStatisticsResponse(
    val totalInspections: Int,
    val passRate: Float,
    val averageInspectionTime: Long,
    val aiAccuracy: Float,
    val humanOverrideRate: Float,
    val defectDistribution: Map<DefectType, Int>,
    val trends: List<StatisticsTrend>
)

@Serializable
data class StatisticsTrend(
    val date: String,
    val totalInspections: Int,
    val passRate: Float,
    val defectCount: Int
)

@Serializable
data class ReportRequest(
    val type: ReportType,
    val startDate: Long,
    val endDate: Long,
    val filters: Map<String, String> = emptyMap(),
    val format: ReportFormat = ReportFormat.JSON
)

@Serializable
enum class ReportType {
    INSPECTION_SUMMARY, DEFECT_ANALYSIS, INSPECTOR_PERFORMANCE, TRACEABILITY
}

@Serializable
enum class ReportFormat {
    JSON, PDF, CSV, EXCEL
}

@Serializable
data class InspectionReport(
    val reportId: String,
    val type: ReportType,
    val generatedAt: Long,
    val data: Map<String, JsonElement>,
    val downloadUrl: String? = null
)

@Serializable
data class RealtimeInspectionRequest(
    val deviceId: String,
    val productId: String,
    val inspectionParameters: Map<String, String> = emptyMap(),
    val streamQuality: StreamQuality = StreamQuality.BALANCED
)

@Serializable
enum class StreamQuality {
    LOW, BALANCED, HIGH, ULTRA
}

@Serializable
data class RealtimeSession(
    val sessionId: String,
    val deviceId: String,
    val streamEndpoint: String,
    val controlEndpoint: String,
    val expiresAt: Long
)

@Serializable
data class BatchSubmissionResult(
    val totalSubmitted: Int,
    val successful: Int,
    val failed: Int,
    val errors: Map<String, String> = emptyMap()
)

@Serializable
data class InspectionSyncResponse(
    val updates: List<Inspection>,
    val deletions: List<String>,
    val syncTimestamp: Long,
    val conflicts: List<SyncConflict> = emptyList()
)

@Serializable
data class SyncConflict(
    val inspectionId: String,
    val conflictType: ConflictType,
    val localVersion: Inspection,
    val serverVersion: Inspection
)

@Serializable
enum class ConflictType {
    CONCURRENT_MODIFICATION, VERSION_MISMATCH, DATA_CORRUPTION
}
