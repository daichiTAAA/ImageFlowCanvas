package com.imageflow.kmp.network.impl

import com.imageflow.kmp.models.Inspection
import com.imageflow.kmp.network.*
import kotlinx.serialization.json.Json
import kotlinx.serialization.decodeFromString

class KtorInspectionApiService(
    private val rest: RestClient,
    private val json: Json = Json { ignoreUnknownKeys = true; isLenient = true }
) : InspectionApiService {

    override suspend fun submitForAiInspection(request: AiInspectionRequest): ApiResult<com.imageflow.kmp.models.AiInspectionResult> =
        ApiResult.NetworkError("REST submit not implemented; use gRPC in production")

    override suspend fun getAiInspectionStatus(requestId: String): ApiResult<AiInspectionStatus> =
        runCatching {
            val body = rest.get("inspection-executions/${'$'}requestId")
            val status = json.decodeFromString<AiInspectionStatus>(body)
            ApiResult.Success(status)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun uploadInspectionImage(inspectionId: String, imagePath: String): ApiResult<FileUploadResult> =
        ApiResult.Error("NOT_IMPLEMENTED", "File upload should use multipart; not available via simple RestClient")

    override suspend fun uploadInspectionVideo(inspectionId: String, videoPath: String): ApiResult<FileUploadResult> =
        ApiResult.Error("NOT_IMPLEMENTED", "File upload should use multipart; not available via simple RestClient")

    override suspend fun createInspection(inspection: Inspection): ApiResult<Inspection> =
        ApiResult.Error("NOT_IMPLEMENTED", "Create via REST POST not implemented in RestClient yet")

    override suspend fun updateInspection(inspection: Inspection): ApiResult<Inspection> =
        ApiResult.Error("NOT_IMPLEMENTED", "Update via REST PATCH not implemented in RestClient yet")

    override suspend fun submitInspectionResult(inspectionId: String, result: InspectionSubmission): ApiResult<InspectionResponse> =
        ApiResult.Error("NOT_IMPLEMENTED", "Submit result via REST POST not implemented in RestClient yet")

    override suspend fun getInspectionHistory(productId: String): ApiResult<List<Inspection>> =
        runCatching {
            val body = rest.get("inspection-executions?product_id=${'$'}productId")
            val list = json.decodeFromString<List<Inspection>>(body)
            ApiResult.Success(list)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun submitHumanReview(review: HumanReviewSubmission): ApiResult<HumanReviewResponse> =
        ApiResult.Error("NOT_IMPLEMENTED", "Human review submit not implemented in RestClient")

    override suspend fun getInspectionsForReview(inspectorId: String): ApiResult<List<Inspection>> =
        runCatching {
            val body = rest.get("inspection-executions?inspector_id=${'$'}inspectorId&state=HUMAN_REVIEW")
            val list = json.decodeFromString<List<Inspection>>(body)
            ApiResult.Success(list)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun updateReviewStatus(inspectionId: String, status: String): ApiResult<Boolean> =
        ApiResult.Error("NOT_IMPLEMENTED", "Review status update not implemented in RestClient")

    override suspend fun getInspectionStatistics(request: StatisticsRequest): ApiResult<InspectionStatisticsResponse> =
        ApiResult.Error("NOT_IMPLEMENTED", "Statistics endpoint not wired")

    override suspend fun generateInspectionReport(request: ReportRequest): ApiResult<InspectionReport> =
        ApiResult.Error("NOT_IMPLEMENTED", "Report generation endpoint not wired")

    override suspend fun startRealtimeInspection(request: RealtimeInspectionRequest): ApiResult<RealtimeSession> =
        ApiResult.Error("NOT_IMPLEMENTED", "Realtime session should use WebSocket/gRPC")

    override suspend fun stopRealtimeInspection(sessionId: String): ApiResult<Boolean> =
        ApiResult.Error("NOT_IMPLEMENTED", "Realtime stop not implemented")

    override suspend fun submitInspectionBatch(inspections: List<Inspection>): ApiResult<BatchSubmissionResult> =
        ApiResult.Error("NOT_IMPLEMENTED", "Batch submit not implemented in RestClient")

    override suspend fun syncInspectionData(lastSyncTime: Long): ApiResult<InspectionSyncResponse> =
        runCatching {
            val body = rest.get("inspection-executions/sync?last_sync=${'$'}lastSyncTime")
            val resp = json.decodeFromString<InspectionSyncResponse>(body)
            ApiResult.Success(resp)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun getInspectionItemsForProduct(
        productId: String,
        processCode: String,
        page: Int,
        pageSize: Int
    ): ApiResult<PaginatedResponse<InspectionItemKmp>> =
        runCatching {
            val body = rest.get("inspection/products/$productId/processes/$processCode/items?page=$page&page_size=$pageSize")
            val resp = json.decodeFromString<PaginatedResponse<InspectionItemKmp>>(body)
            ApiResult.Success(resp)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun getInspectionCriteria(criteriaId: String): ApiResult<InspectionCriteriaKmp> =
        runCatching {
            val body = rest.get("inspection/criterias/$criteriaId")
            val resp = json.decodeFromString<InspectionCriteriaKmp>(body)
            ApiResult.Success(resp)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun listProcesses(page: Int, pageSize: Int): ApiResult<PaginatedResponse<ProcessMasterKmp>> =
        runCatching {
            val body = rest.get("inspection/processes?page=$page&page_size=$pageSize")
            val resp = json.decodeFromString<PaginatedResponse<ProcessMasterKmp>>(body)
            ApiResult.Success(resp)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun createExecution(
        instructionId: String,
        operatorId: String?,
        qrCode: String?,
        metadata: Map<String, String>
    ): ApiResult<ExecuteInspectionResponseKmp> = runCatching {
        val payload = buildString {
            append("{")
            append("\"instruction_id\":\"$instructionId\"")
            if (!operatorId.isNullOrBlank()) append(",\"operator_id\":\"$operatorId\"")
            if (!qrCode.isNullOrBlank()) append(",\"qr_code\":\"$qrCode\"")
            if (metadata.isNotEmpty()) {
                val metaJson = metadata.entries.joinToString(prefix = "{", postfix = "}") { (k, v) -> "\"${k}\":\"${v}\"" }
                append(",\"metadata\":$metaJson")
            }
            append("}")
        }
        val body = rest.postJson("inspection/executions", payload)
        val resp = json.decodeFromString<ExecuteInspectionResponseKmp>(body)
        ApiResult.Success(resp)
    }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun listItemExecutions(executionId: String): ApiResult<List<InspectionItemExecutionKmp>> = runCatching {
        val body = rest.get("inspection/executions/$executionId/items")
        val resp = json.decodeFromString<List<InspectionItemExecutionKmp>>(body)
        ApiResult.Success(resp)
    }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun saveInspectionResult(
        executionId: String,
        itemExecutionId: String,
        judgment: JudgmentResultKmp,
        comment: String?,
        metrics: Map<String, String>,
        evidenceFileIds: List<String>
    ): ApiResult<InspectionResultKmp> = runCatching {
        val payload = buildString {
            append("{")
            append("\"execution_id\":\"$executionId\",")
            append("\"item_execution_id\":\"$itemExecutionId\",")
            append("\"judgment\":\"$judgment\"")
            if (!comment.isNullOrBlank()) append(",\"comment\":\"$comment\"")
            if (metrics.isNotEmpty()) {
                val metaJson = metrics.entries.joinToString(prefix = "{", postfix = "}") { (k, v) -> "\"${k}\":\"${v}\"" }
                append(",\"metrics\":$metaJson")
            }
            if (evidenceFileIds.isNotEmpty()) {
                val arr = evidenceFileIds.joinToString(prefix = "[", postfix = "]") { "\"$it\"" }
                append(",\"evidence_file_ids\":$arr")
            }
            append("}")
        }
        val body = rest.postJson("inspection/results", payload)
        val resp = json.decodeFromString<InspectionResultKmp>(body)
        ApiResult.Success(resp)
    }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun uploadImageBytes(bytes: ByteArray, filename: String, contentType: String): ApiResult<FileUploadResult> = runCatching {
        val body = rest.postMultipartBytes("files/", fieldName = "file", filename = filename, bytes = bytes, contentType = contentType)
        val resp = json.decodeFromString<FileUploadResult>(body)
        ApiResult.Success(resp)
    }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }
}
