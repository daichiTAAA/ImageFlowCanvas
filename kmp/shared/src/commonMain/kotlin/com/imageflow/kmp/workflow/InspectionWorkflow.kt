package com.imageflow.kmp.workflow

import com.imageflow.kmp.state.InspectionState
import com.imageflow.kmp.models.*
import kotlinx.coroutines.flow.StateFlow

// Enhanced inspection workflow interface based on F-021 through F-024 requirements
interface InspectionWorkflow {
    val state: StateFlow<InspectionState>
    val currentInspection: StateFlow<Inspection?>
    val progress: StateFlow<InspectionProgress>
    
    // Core workflow methods
    suspend fun start()
    suspend fun cancel()
    suspend fun pause()
    suspend fun resume()
    
    // Product identification methods (F-021-1, F-021-2)
    suspend fun scanQrCode(rawData: String): QrScanResult
    suspend fun searchProductInfo(searchQuery: ProductSearchQuery): ProductSearchResult
    suspend fun selectProduct(productInfo: ProductInfo): Boolean
    
    // Inspection execution methods (F-022)
    suspend fun startInspection(inspectionType: InspectionType): Boolean
    suspend fun captureImage(imagePath: String): Boolean
    suspend fun captureVideo(videoPath: String): Boolean
    suspend fun processAiInspection(): AiInspectionResult
    
    // Human verification methods (F-023)
    suspend fun reviewAiResults(review: HumanReview): Boolean
    suspend fun addHumanComments(comments: String): Boolean
    suspend fun finalizeInspection(result: HumanResult): Boolean
    
    // State management
    suspend fun transitionToState(newState: InspectionState): Boolean
    suspend fun getCurrentProgress(): InspectionProgress
    
    // Data persistence
    suspend fun saveInspection(): Boolean
    suspend fun loadInspection(inspectionId: String): Boolean
}

data class InspectionProgress(
    val currentStep: Int,
    val totalSteps: Int,
    val completedItems: Int,
    val totalItems: Int,
    val estimatedTimeRemaining: Long? = null,
    val overallStatus: InspectionState
) {
    val completionPercentage: Float
        get() = if (totalItems > 0) completedItems.toFloat() / totalItems else 0f
}

data class ProductSearchQuery(
    val workOrderId: String? = null,
    val instructionId: String? = null,
    val productType: String? = null,
    val machineNumber: String? = null,
    val productionDateRange: DateRange? = null,
    val limit: Int = 50
)

data class DateRange(
    val startDate: String,
    val endDate: String
)

data class ProductSearchResult(
    val products: List<ProductInfo>,
    val totalCount: Int,
    val query: ProductSearchQuery,
    val searchTimeMs: Long
)

data class HumanReview(
    val inspectionId: String,
    val overallResult: HumanResult,
    val reviewedDefects: List<DefectReview> = emptyList(),
    val comments: String? = null,
    val reviewerId: String
)

data class DefectReview(
    val defectId: String,
    val humanResult: HumanResult,
    val confidence: Float,
    val comments: String? = null
)

