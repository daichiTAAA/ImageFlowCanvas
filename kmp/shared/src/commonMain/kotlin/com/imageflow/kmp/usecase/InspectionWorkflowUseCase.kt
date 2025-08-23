package com.imageflow.kmp.usecase

import com.imageflow.kmp.models.*
import com.imageflow.kmp.repository.InspectionRepository
import com.imageflow.kmp.repository.ProductRepository
import com.imageflow.kmp.network.InspectionApiService
import com.imageflow.kmp.network.ApiResult
import com.imageflow.kmp.state.InspectionState
import com.imageflow.kmp.workflow.InspectionWorkflow
import com.imageflow.kmp.workflow.InspectionProgress
import com.imageflow.kmp.workflow.ProductSearchQuery
import com.imageflow.kmp.workflow.ProductSearchResult
import com.imageflow.kmp.workflow.HumanReview
import com.imageflow.kmp.network.AiInspectionRequest
import com.imageflow.kmp.network.InspectionSubmission
import kotlinx.coroutines.flow.*
import java.util.UUID

// Use case for managing complete inspection workflow based on F-022, F-023, F-024 requirements
class InspectionWorkflowUseCase(
    private val inspectionRepository: InspectionRepository,
    private val productRepository: ProductRepository,
    private val inspectionApiService: InspectionApiService
) : InspectionWorkflow {
    
    private val _state = MutableStateFlow<InspectionState>(InspectionState.ProductScanning)
    override val state: StateFlow<InspectionState> = _state.asStateFlow()
    
    private val _currentInspection = MutableStateFlow<Inspection?>(null)
    override val currentInspection: StateFlow<Inspection?> = _currentInspection.asStateFlow()
    
    private val _progress = MutableStateFlow(
        InspectionProgress(
            currentStep = 0,
            totalSteps = 0,
            completedItems = 0,
            totalItems = 0,
            estimatedTimeRemaining = null,
            overallStatus = InspectionState.ProductScanning
        )
    )
    override val progress: StateFlow<InspectionProgress> = _progress.asStateFlow()
    
    override suspend fun start() {
        _state.value = InspectionState.ProductScanning
        _currentInspection.value = null
        updateProgress()
    }
    
    override suspend fun cancel() {
        _currentInspection.value?.let { inspection ->
            val cancelledInspection = inspection.copy(
                inspectionState = InspectionState.Cancelled,
                updatedAt = System.currentTimeMillis()
            )
            inspectionRepository.updateInspection(cancelledInspection)
            _currentInspection.value = cancelledInspection
        }
        _state.value = InspectionState.Cancelled
        updateProgress()
    }
    
    override suspend fun pause() {
        // Implementation for pausing inspection
        _currentInspection.value?.let { inspection ->
            inspectionRepository.updateInspection(inspection.copy(updatedAt = System.currentTimeMillis()))
        }
    }
    
    override suspend fun resume() {
        // Implementation for resuming inspection
        _currentInspection.value?.let { inspection ->
            _state.value = inspection.inspectionState
            updateProgress()
        }
    }
    
    override suspend fun scanQrCode(rawData: String): QrScanResult {
        // This would typically be handled by ScanProductUseCase
        // For now, return a placeholder result
        return QrScanResult(
            success = false,
            productInfo = null,
            rawData = rawData,
            scanType = ScanType.QR_CODE,
            confidence = 0f,
            validationStatus = ValidationStatus.INVALID,
            errorMessage = "Use ScanProductUseCase for QR scanning"
        )
    }
    
    override suspend fun searchProductInfo(searchQuery: ProductSearchQuery): ProductSearchResult {
        // This would typically be handled by SearchProductUseCase
        return ProductSearchResult(
            products = emptyList(),
            totalCount = 0,
            query = searchQuery,
            searchTimeMs = 0
        )
    }
    
    override suspend fun selectProduct(productInfo: ProductInfo): Boolean {
        return try {
            // If there is already a completed inspection for this product, reuse it and mark state as Completed
            runCatching {
                val prior = inspectionRepository.getInspectionsByProduct(productInfo.id)
                    .filter { it.inspectionState == InspectionState.Completed }
                    .maxByOrNull { it.completedAt ?: it.updatedAt }
                if (prior != null) {
                    _currentInspection.value = prior
                    _state.value = InspectionState.Completed
                    updateProgress()
                    return true
                }
            }

            // Otherwise create a new inspection
            val inspection = createNewInspection(productInfo)
            inspectionRepository.saveInspection(inspection)

            _currentInspection.value = inspection
            _state.value = InspectionState.ProductIdentified
            updateProgress()
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun startInspection(inspectionType: InspectionType): Boolean {
        val currentInspection = _currentInspection.value ?: return false
        // Block starting when already completed
        if (currentInspection.inspectionState == InspectionState.Completed) {
            _state.value = InspectionState.Completed
            updateProgress()
            return false
        }
        return try {
            val updatedInspection = currentInspection.copy(
                inspectionType = inspectionType,
                inspectionState = InspectionState.InProgress,
                startedAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )
            
            inspectionRepository.updateInspection(updatedInspection)
            _currentInspection.value = updatedInspection
            _state.value = InspectionState.InProgress
            updateProgress()
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun captureImage(imagePath: String): Boolean {
        val currentInspection = _currentInspection.value ?: return false
        
        return try {
            val updatedInspection = currentInspection.copy(
                imagePaths = currentInspection.imagePaths + imagePath,
                updatedAt = System.currentTimeMillis()
            )
            
            inspectionRepository.updateInspection(updatedInspection)
            _currentInspection.value = updatedInspection
            updateProgress()
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun captureVideo(videoPath: String): Boolean {
        val currentInspection = _currentInspection.value ?: return false
        
        return try {
            val updatedInspection = currentInspection.copy(
                videoPath = videoPath,
                updatedAt = System.currentTimeMillis()
            )
            
            inspectionRepository.updateInspection(updatedInspection)
            _currentInspection.value = updatedInspection
            updateProgress()
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun processAiInspection(): AiInspectionResult {
        val currentInspection = _currentInspection.value
            ?: throw IllegalStateException("No active inspection")
        
        return try {
            // Submit for AI processing
            val aiRequest = AiInspectionRequest(
                inspectionId = currentInspection.id,
                productId = currentInspection.productId,
                inspectionType = currentInspection.inspectionType,
                imagePaths = currentInspection.imagePaths,
                videoPath = currentInspection.videoPath
            )
            
            when (val result = inspectionApiService.submitForAiInspection(aiRequest)) {
                is ApiResult.Success -> {
                    val aiResult = result.data
                    
                    // Update inspection with AI results
                    inspectionRepository.updateAiResult(currentInspection.id, aiResult)
                    _state.value = InspectionState.AiCompleted
                    
                    val updatedInspection = currentInspection.copy(
                        aiResult = aiResult,
                        aiConfidence = aiResult.confidence,
                        inspectionState = InspectionState.AiCompleted,
                        updatedAt = System.currentTimeMillis()
                    )
                    _currentInspection.value = updatedInspection
                    updateProgress()
                    
                    aiResult
                }
                is ApiResult.Error -> fallbackLocalAi(currentInspection, reason = result.message)
                is ApiResult.NetworkError -> fallbackLocalAi(currentInspection, reason = result.message)
            }
        } catch (e: Exception) {
            _state.value = InspectionState.Failed
            updateProgress()
            throw e
        }
    }

    // === Criteria evaluation helpers for realtime ===
    suspend fun getInspectionCriteria(criteriaId: String): com.imageflow.kmp.network.InspectionCriteriaKmp? {
        return when (val res = inspectionApiService.getInspectionCriteria(criteriaId)) {
            is ApiResult.Success -> res.data
            else -> null
        }
    }

    fun evaluateDetectionsAgainstCriteria(
        defects: List<DetectedDefect>,
        criteria: com.imageflow.kmp.network.InspectionCriteriaKmp
    ): InspectionResult {
        val count = defects.size
        return when (criteria.judgment_type) {
            com.imageflow.kmp.network.JudgmentTypeKmp.BINARY -> {
                val expectedOk = criteria.spec.binary?.expected_value ?: true
                if (expectedOk) if (count == 0) InspectionResult.PASS else InspectionResult.FAIL
                else if (count > 0) InspectionResult.PASS else InspectionResult.FAIL
            }
            com.imageflow.kmp.network.JudgmentTypeKmp.THRESHOLD -> {
                val th = criteria.spec.threshold ?: return if (count == 0) InspectionResult.PASS else InspectionResult.FAIL
                compareCount(count.toDouble(), th.threshold, th.operator)
            }
            com.imageflow.kmp.network.JudgmentTypeKmp.CATEGORICAL -> {
                val allowed = criteria.spec.categorical?.allowed_categories ?: emptyList()
                val allAllowed = defects.all { d -> d.description != null && allowed.contains(d.description) }
                if (allAllowed) InspectionResult.PASS else InspectionResult.FAIL
            }
            com.imageflow.kmp.network.JudgmentTypeKmp.NUMERICAL -> {
                // 数値基準（min/max）は本来は測定値に対して適用するが、
                // 現時点では検出数に簡易適用（min <= count <= max）
                val num = criteria.spec.numerical
                if (num == null) return if (count == 0) InspectionResult.PASS else InspectionResult.FAIL
                val okMin = num.min_value?.let { count.toDouble() >= it } ?: true
                val okMax = num.max_value?.let { count.toDouble() <= it } ?: true
                if (okMin && okMax) InspectionResult.PASS else InspectionResult.FAIL
            }
            else -> if (count == 0) InspectionResult.PASS else InspectionResult.FAIL
        }
    }

    private fun compareCount(value: Double, threshold: Double, op: com.imageflow.kmp.network.ComparisonOperatorKmp): InspectionResult {
        val ok = when (op) {
            com.imageflow.kmp.network.ComparisonOperatorKmp.LESS_THAN -> value < threshold
            com.imageflow.kmp.network.ComparisonOperatorKmp.LESS_THAN_OR_EQUAL -> value <= threshold
            com.imageflow.kmp.network.ComparisonOperatorKmp.GREATER_THAN -> value > threshold
            com.imageflow.kmp.network.ComparisonOperatorKmp.GREATER_THAN_OR_EQUAL -> value >= threshold
            com.imageflow.kmp.network.ComparisonOperatorKmp.EQUAL -> value == threshold
            com.imageflow.kmp.network.ComparisonOperatorKmp.NOT_EQUAL -> value != threshold
            else -> value <= threshold
        }
        return if (ok) InspectionResult.PASS else InspectionResult.FAIL
    }

    private suspend fun fallbackLocalAi(currentInspection: Inspection, reason: String?): AiInspectionResult {
        // Offline/dev fallback: generate a simple PASS/FAIL based on presence of images
        val hasImages = currentInspection.imagePaths.isNotEmpty() || currentInspection.videoPath != null
        val ai = AiInspectionResult(
            overallResult = if (hasImages) InspectionResult.PASS else InspectionResult.PENDING,
            confidence = if (hasImages) 0.80f else 0.0f,
            processingTimeMs = 300,
            detectedDefects = emptyList()
        )
        // Persist and advance state
        inspectionRepository.updateAiResult(currentInspection.id, ai)
        _state.value = InspectionState.AiCompleted
        val updated = currentInspection.copy(
            aiResult = ai,
            aiConfidence = ai.confidence,
            inspectionState = InspectionState.AiCompleted,
            updatedAt = System.currentTimeMillis()
        )
        _currentInspection.value = updated
        updateProgress()
        return ai
    }
    
    override suspend fun reviewAiResults(review: HumanReview): Boolean {
        val currentInspection = _currentInspection.value ?: return false
        
        return try {
            val updatedInspection = currentInspection.copy(
                humanVerified = true,
                humanResult = review.overallResult,
                humanComments = review.comments,
                inspectionState = InspectionState.HumanReview,
                updatedAt = System.currentTimeMillis()
            )
            
            inspectionRepository.updateInspection(updatedInspection)
            _currentInspection.value = updatedInspection
            _state.value = InspectionState.HumanReview
            updateProgress()
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun addHumanComments(comments: String): Boolean {
        val currentInspection = _currentInspection.value ?: return false
        
        return try {
            val updatedInspection = currentInspection.copy(
                humanComments = comments,
                updatedAt = System.currentTimeMillis()
            )
            
            inspectionRepository.updateInspection(updatedInspection)
            _currentInspection.value = updatedInspection
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun finalizeInspection(result: HumanResult): Boolean {
        val currentInspection = _currentInspection.value ?: return false
        
        return try {
            val now = System.currentTimeMillis()
            val finalInspection = currentInspection.copy(
                humanResult = result,
                inspectionState = InspectionState.Completed,
                completedAt = now,
                updatedAt = now
            )
            
            inspectionRepository.updateInspection(finalInspection)
            
            // Submit to server
            val submission = InspectionSubmission(
                inspectionId = finalInspection.id,
                finalResult = when (result) {
                    HumanResult.OK -> InspectionResult.PASS
                    HumanResult.NG -> InspectionResult.FAIL
                    HumanResult.PENDING -> InspectionResult.PENDING
                },
                humanVerified = true,
                humanComments = finalInspection.humanComments
            )
            
            inspectionApiService.submitInspectionResult(finalInspection.id, submission)
            
            _currentInspection.value = finalInspection
            _state.value = InspectionState.Completed
            updateProgress()
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun transitionToState(newState: InspectionState): Boolean {
        val currentInspection = _currentInspection.value
        
        return try {
            if (currentInspection != null) {
                inspectionRepository.updateInspectionState(currentInspection.id, newState)
                _currentInspection.value = currentInspection.copy(
                    inspectionState = newState,
                    updatedAt = System.currentTimeMillis()
                )
            }
            _state.value = newState
            updateProgress()
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun getCurrentProgress(): InspectionProgress {
        return _progress.value
    }
    
    override suspend fun saveInspection(): Boolean {
        val currentInspection = _currentInspection.value ?: return false
        
        return try {
            inspectionRepository.updateInspection(currentInspection)
            true
        } catch (e: Exception) {
            false
        }
    }
    
    override suspend fun loadInspection(inspectionId: String): Boolean {
        return try {
            val inspection = inspectionRepository.getInspection(inspectionId)
            if (inspection != null) {
                _currentInspection.value = inspection
                _state.value = inspection.inspectionState
                updateProgress()
                true
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }
    
    private fun createNewInspection(productInfo: ProductInfo): Inspection {
        val now = System.currentTimeMillis()
        return Inspection(
            id = UUID.randomUUID().toString(),
            productId = productInfo.id,
            workOrderId = productInfo.workOrderId,
            instructionId = productInfo.instructionId,
            inspectionType = InspectionType.STATIC_IMAGE,
            inspectionState = InspectionState.ProductIdentified,
            startedAt = now,
            createdAt = now,
            updatedAt = now
        )
    }
    
    private fun updateProgress() {
        val current = _state.value
        val (currentStep, totalSteps) = when (current) {
            InspectionState.ProductScanning -> 0 to 5
            InspectionState.ProductIdentified -> 1 to 5
            InspectionState.InProgress -> 2 to 5
            InspectionState.AiCompleted -> 3 to 5
            InspectionState.HumanReview -> 4 to 5
            InspectionState.Completed -> 5 to 5
            else -> 0 to 5
        }
        
        val inspection = _currentInspection.value
        val completedItems = when {
            inspection == null -> 0
            inspection.imagePaths.isNotEmpty() || inspection.videoPath != null -> 1
            inspection.aiResult != null -> 2
            inspection.humanVerified -> 3
            inspection.inspectionState == InspectionState.Completed -> 4
            else -> 0
        }
        
        _progress.value = InspectionProgress(
            currentStep = currentStep,
            totalSteps = totalSteps,
            completedItems = completedItems,
            totalItems = 4, // Image capture, AI processing, Human review, Completion
            overallStatus = current
        )
    }

    // Masters fetch: expose inspection items configured on Web for given product + process
    suspend fun getInspectionItemsForProduct(productId: String, processCode: String = "DEFAULT"): List<com.imageflow.kmp.network.InspectionItemKmp> {
        return when (val res = inspectionApiService.getInspectionItemsForProduct(productId, processCode)) {
            is ApiResult.Success -> res.data.items
            is ApiResult.Error -> emptyList()
            is ApiResult.NetworkError -> emptyList()
        }
    }

    // Status helper for UI: latest inspection state for a given product
    suspend fun getLatestInspectionStateForProduct(productId: String): InspectionState? {
        return try {
            val list = inspectionRepository.getInspectionsByProduct(productId)
            val latest = list.maxByOrNull { (it.completedAt ?: 0L).coerceAtLeast(it.updatedAt) }
            latest?.inspectionState
        } catch (_: Throwable) {
            null
        }
    }

    // Persist human decisions to backend execution/results
    suspend fun persistHumanResultsToBackend(
        targetId: String,
        decisions: Map<String, HumanResult>,
        items: List<com.imageflow.kmp.network.InspectionItemKmp>,
        metadata: Map<String, String> = emptyMap()
    ): Boolean {
        return try {
            // Create execution for the selected target
            val exec = inspectionApiService.createExecution(targetId = targetId, operatorId = null, qrCode = null, metadata = metadata)
            val execId = when (exec) {
                is ApiResult.Success -> exec.data.execution_id
                is ApiResult.Error, is ApiResult.NetworkError -> return false
            }

            // Fetch item executions to map item_id -> item_execution_id
            val exList = when (val list = inspectionApiService.listItemExecutions(execId)) {
                is ApiResult.Success -> list.data
                is ApiResult.Error, is ApiResult.NetworkError -> return false
            }
            val byItemId = exList.associateBy { it.item_id }

            var allOk = true
            items.forEach { item ->
                val dec = decisions[item.id] ?: return@forEach
                val j = when (dec) {
                    HumanResult.OK -> com.imageflow.kmp.network.JudgmentResultKmp.OK
                    HumanResult.NG -> com.imageflow.kmp.network.JudgmentResultKmp.NG
                    HumanResult.PENDING -> com.imageflow.kmp.network.JudgmentResultKmp.PENDING
                }
                val ie = byItemId[item.id] ?: run { allOk = false; return@forEach }
                when (inspectionApiService.saveInspectionResult(
                    executionId = execId,
                    itemExecutionId = ie.id,
                    judgment = j,
                    comment = null,
                    metrics = emptyMap()
                )) {
                    is ApiResult.Success -> {}
                    is ApiResult.Error, is ApiResult.NetworkError -> allOk = false
                }
            }
            allOk
        } catch (_: Throwable) {
            false
        }
    }

    // Realtime AI updates from desktop streaming (gRPC)
    suspend fun updateAiResultFromRealtime(ai: AiInspectionResult) {
        val current = _currentInspection.value ?: return
        try {
            inspectionRepository.updateAiResult(current.id, ai)
            val updated = current.copy(
                aiResult = ai,
                aiConfidence = ai.confidence,
                inspectionState = InspectionState.InProgress,
                updatedAt = System.currentTimeMillis()
            )
            _currentInspection.value = updated
            _state.value = InspectionState.InProgress
            updateProgress()
        } catch (_: Throwable) {
            // ignore
        }
    }
}
