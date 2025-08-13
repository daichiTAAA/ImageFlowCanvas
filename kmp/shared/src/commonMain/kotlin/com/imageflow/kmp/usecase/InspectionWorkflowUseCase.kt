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
            // Create new inspection
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
                is ApiResult.Error -> {
                    _state.value = InspectionState.Failed
                    throw Exception("AI inspection failed: ${result.message}")
                }
                is ApiResult.NetworkError -> {
                    _state.value = InspectionState.Failed
                    throw Exception("Network error during AI inspection: ${result.message}")
                }
            }
        } catch (e: Exception) {
            _state.value = InspectionState.Failed
            updateProgress()
            throw e
        }
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
}
