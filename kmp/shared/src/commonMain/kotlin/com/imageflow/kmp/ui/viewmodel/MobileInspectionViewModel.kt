package com.imageflow.kmp.ui.viewmodel

import com.imageflow.kmp.models.*
import com.imageflow.kmp.network.ProductSuggestion
import com.imageflow.kmp.state.InspectionState
import com.imageflow.kmp.usecase.*
import com.imageflow.kmp.workflow.InspectionProgress
import com.imageflow.kmp.workflow.ProductSearchResult
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

// ViewModel for mobile inspection screen - integrates all inspection use cases
class MobileInspectionViewModel(
    private val scanProductUseCase: ScanProductUseCase,
    private val searchProductUseCase: SearchProductUseCase,
    private val inspectionWorkflowUseCase: InspectionWorkflowUseCase,
    private val syncUseCase: SyncUseCase,
    private val viewModelScope: CoroutineScope
) {
    
    // State flows
    private val _uiState = MutableStateFlow(MobileInspectionUiState())
    val uiState: StateFlow<MobileInspectionUiState> = _uiState.asStateFlow()
    
    private val _qrScanResult = MutableStateFlow<QrScanResult?>(null)
    val qrScanResult: StateFlow<QrScanResult?> = _qrScanResult.asStateFlow()
    
    private val _searchResults = MutableStateFlow<ProductSearchResult?>(null)
    val searchResults: StateFlow<ProductSearchResult?> = _searchResults.asStateFlow()

    private val _suggestions = MutableStateFlow<List<ProductSuggestion>>(emptyList())
    val suggestions: StateFlow<List<ProductSuggestion>> = _suggestions.asStateFlow()
    
    // Inspection workflow state
    val inspectionState: StateFlow<InspectionState> = inspectionWorkflowUseCase.state
    val currentInspection: StateFlow<Inspection?> = inspectionWorkflowUseCase.currentInspection
    val inspectionProgress: StateFlow<InspectionProgress> = inspectionWorkflowUseCase.progress
    
    init {
        // Initialize workflow
        viewModelScope.launch {
            inspectionWorkflowUseCase.start()
        }
        
        // Observe state changes
        viewModelScope.launch {
            inspectionState.collect { state ->
                updateUiState { it.copy(inspectionState = state) }
            }
        }
        
        viewModelScope.launch {
            currentInspection.collect { inspection ->
                updateUiState { prev ->
                    val derived = getProductInfoFromInspection(inspection)
                    // Do not overwrite with null; keep previously selected product if available
                    prev.copy(currentProduct = derived ?: prev.currentProduct)
                }
            }
        }
    }
    
    // QR scanning actions
    fun startQrScanning() {
        updateUiState { it.copy(isQrScanningActive = true) }
    }
    
    fun stopQrScanning() {
        updateUiState { it.copy(isQrScanningActive = false) }
        _qrScanResult.value = null
    }
    
    fun processQrScan(rawData: String) {
        viewModelScope.launch {
            updateUiState { it.copy(isLoading = true) }
            try {
                val result = scanProductUseCase.scanQrCode(rawData)
                _qrScanResult.value = result
                
                if (result.success && result.productInfo != null) {
                    selectProduct(result.productInfo)
                }
            } catch (e: Exception) {
                updateUiState { 
                    it.copy(
                        isLoading = false,
                        errorMessage = "QRスキャンエラー: ${e.message}"
                    )
                }
            }
            updateUiState { it.copy(isLoading = false) }
        }
    }
    
    fun acceptQrResult(result: QrScanResult) {
        if (result.success && result.productInfo != null) {
            selectProduct(result.productInfo)
        }
        _qrScanResult.value = null
        updateUiState { it.copy(isQrScanningActive = false) }
    }
    
    fun retryQrScan() {
        _qrScanResult.value = null
    }
    
    // Product search actions
    fun searchProducts(query: String) {
        viewModelScope.launch {
            updateUiState { it.copy(isLoading = true) }
            try {
                val result = searchProductUseCase.searchProducts(query)
                _searchResults.value = result.copy(
                    products = sortByProductionOrder(result.products)
                )
            } catch (e: Throwable) {
                updateUiState {
                    it.copy(
                        errorMessage = "検索エラー: ${e.message ?: e::class.simpleName}"
                    )
                }
            } finally {
                updateUiState { it.copy(isLoading = false) }
            }
        }
    }

    // Advanced search by specific fields
    fun searchProductsAdvanced(productCode: String, machineNumber: String) {
        viewModelScope.launch {
            updateUiState { it.copy(isLoading = true) }
            try {
                val query = com.imageflow.kmp.workflow.ProductSearchQuery(
                    productCode = productCode.ifBlank { null },
                    machineNumber = machineNumber.ifBlank { null },
                    limit = 50
                )
                val result = searchProductUseCase.searchProducts(query)
                _searchResults.value = result.copy(
                    products = sortByProductionOrder(result.products)
                )
            } catch (e: Throwable) {
                updateUiState {
                    it.copy(
                        errorMessage = "検索エラー: ${e.message ?: e::class.simpleName}"
                    )
                }
            } finally {
                updateUiState { it.copy(isLoading = false) }
            }
        }
    }

    fun loadSuggestions(partial: String) {
        viewModelScope.launch {
            try {
                _suggestions.value = searchProductUseCase.getProductSuggestions(partial)
            } catch (_: Exception) {
                _suggestions.value = emptyList()
            }
        }
    }
    
    fun selectProduct(productInfo: ProductInfo) {
        viewModelScope.launch {
            try {
                val success = inspectionWorkflowUseCase.selectProduct(productInfo)
                if (success) {
                    updateUiState { 
                        it.copy(
                            currentProduct = productInfo,
                            isQrScanningActive = false
                        )
                    }
                    // Fetch inspection items configured on Web for this product with selected process code
                    runCatching {
                        val selectedProcess = com.imageflow.kmp.di.DependencyContainer.currentProcessCode()
                        val items = inspectionWorkflowUseCase.getInspectionItemsForProduct(productInfo.id, processCode = selectedProcess)
                        updateUiState { prev -> prev.copy(inspectionItems = items) }
                    }
                    clearSearchResults()
                }
            } catch (e: Exception) {
                updateUiState { 
                    it.copy(errorMessage = "型式選択エラー: ${e.message}")
                }
            }
        }
    }
    
    fun selectProductById(productId: String) {
        viewModelScope.launch {
            updateUiState { it.copy(isLoading = true) }
            try {
                when (val res = searchProductUseCase.getProductById(productId)) {
                    is com.imageflow.kmp.network.ApiResult.Success -> {
                        selectProduct(res.data)
                    }
                    is com.imageflow.kmp.network.ApiResult.Error -> {
                        updateUiState { it.copy(errorMessage = "型式取得エラー: ${res.message}") }
                    }
                    is com.imageflow.kmp.network.ApiResult.NetworkError -> {
                        updateUiState { it.copy(errorMessage = "ネットワークエラー: ${res.message}") }
                    }
                }
            } catch (e: Exception) {
                updateUiState { it.copy(errorMessage = "型式取得エラー: ${e.message}") }
            } finally {
                updateUiState { it.copy(isLoading = false) }
            }
        }
    }
    
    fun clearSearchResults() {
        _searchResults.value = null
        _suggestions.value = emptyList()
    }

    fun resetToScanning() {
        viewModelScope.launch {
            try {
                // Transition workflow back to scanning and clear current product in UI
                inspectionWorkflowUseCase.transitionToState(InspectionState.ProductScanning)
                updateUiState { it.copy(currentProduct = null) }
            } catch (_: Exception) {
                // no-op
            }
        }
    }
    
    // Inspection actions
    fun startInspection(inspectionType: InspectionType = InspectionType.STATIC_IMAGE) {
        viewModelScope.launch {
            try {
                val success = inspectionWorkflowUseCase.startInspection(inspectionType)
                if (!success) {
                    updateUiState { 
                        it.copy(errorMessage = "検査開始に失敗しました")
                    }
                }
            } catch (e: Exception) {
                updateUiState { 
                    it.copy(errorMessage = "検査開始エラー: ${e.message}")
                }
            }
        }
    }
    
    fun captureImage(imagePath: String) {
        viewModelScope.launch {
            try {
                val success = inspectionWorkflowUseCase.captureImage(imagePath)
                if (!success) {
                    updateUiState { 
                        it.copy(errorMessage = "画像キャプチャに失敗しました")
                    }
                }
            } catch (e: Exception) {
                updateUiState { 
                    it.copy(errorMessage = "画像キャプチャエラー: ${e.message}")
                }
            }
        }
    }
    
    fun processAiInspection() {
        viewModelScope.launch {
            updateUiState { it.copy(isLoading = true) }
            try {
                val aiResult = inspectionWorkflowUseCase.processAiInspection()
                updateUiState { 
                    it.copy(
                        isLoading = false,
                        lastAiResult = aiResult
                    )
                }
            } catch (e: Exception) {
                updateUiState { 
                    it.copy(
                        isLoading = false,
                        errorMessage = "AI検査エラー: ${e.message}"
                    )
                }
            }
        }
    }
    
    fun submitHumanReview(result: HumanResult, comments: String? = null) {
        viewModelScope.launch {
            try {
                val success = inspectionWorkflowUseCase.finalizeInspection(result)
                if (success) {
                    updateUiState { 
                        it.copy(lastHumanResult = result)
                    }
                } else {
                    updateUiState { 
                        it.copy(errorMessage = "検査結果の送信に失敗しました")
                    }
                }
            } catch (e: Exception) {
                updateUiState { 
                    it.copy(errorMessage = "検査結果送信エラー: ${e.message}")
                }
            }
        }
    }

    // Desktop realtime streaming -> update AI result + state
    fun onRealtimeAiUpdate(detections: Int, processingTimeMs: Long, pipelineId: String? = null) {
        viewModelScope.launch {
            try {
                val ai = AiInspectionResult(
                    overallResult = if (detections == 0) InspectionResult.PASS else InspectionResult.FAIL,
                    detectedDefects = if (detections <= 0) emptyList() else List(detections) {
                        DetectedDefect(
                            type = DefectType.OTHER,
                            location = BoundingBox(0f, 0f, 0f, 0f),
                            severity = if (detections == 0) DefectSeverity.INFO else DefectSeverity.MAJOR,
                            confidence = 0.5f
                        )
                    },
                    measurements = emptyList(),
                    confidence = if (detections == 0) 0.90f else 0.70f,
                    processingTimeMs = processingTimeMs,
                    pipelineId = pipelineId
                )
                inspectionWorkflowUseCase.updateAiResultFromRealtime(ai)
                updateUiState { it.copy(lastAiResult = ai) }
            } catch (_: Throwable) {
                // ignore ui update errors
            }
        }
    }
    
    fun cancelInspection() {
        viewModelScope.launch {
            inspectionWorkflowUseCase.cancel()
            updateUiState { 
                it.copy(
                    currentProduct = null,
                    lastAiResult = null,
                    lastHumanResult = null
                )
            }
        }
    }
    
    // Sync actions
    fun syncData() {
        viewModelScope.launch {
            updateUiState { it.copy(isSyncing = true) }
            try {
                val result = syncUseCase.syncInspections()
                updateUiState { 
                    it.copy(
                        isSyncing = false,
                        lastSyncResult = result
                    )
                }
                
                if (result.hasErrors) {
                    updateUiState { 
                        it.copy(errorMessage = "同期中にエラーが発生しました")
                    }
                }
            } catch (e: Exception) {
                updateUiState { 
                    it.copy(
                        isSyncing = false,
                        errorMessage = "同期エラー: ${e.message}"
                    )
                }
            }
        }
    }
    
    // UI state management
    fun clearErrorMessage() {
        updateUiState { it.copy(errorMessage = null) }
    }
    
    fun setTorchEnabled(enabled: Boolean) {
        updateUiState { it.copy(torchEnabled = enabled) }
    }
    
    private fun updateUiState(update: (MobileInspectionUiState) -> MobileInspectionUiState) {
        _uiState.value = update(_uiState.value)
    }
    
    private fun getProductInfoFromInspection(inspection: Inspection?): ProductInfo? {
        // If needed, reconstruct minimal info from inspection to avoid clearing UI
        return if (inspection != null) {
            // Keep existing UI product unless we can enrich; for now return null to preserve previous via caller
            null
        } else null
    }

    private fun sortByProductionOrder(list: List<ProductInfo>): List<ProductInfo> {
        // Sort by productionDate (YYYY-MM-DD) and monthlySequence, latest first
        return list.sortedWith(compareByDescending<ProductInfo> { it.productionDate }
            .thenByDescending { it.monthlySequence })
    }
}

// UI state data class
data class MobileInspectionUiState(
    val inspectionState: InspectionState = InspectionState.ProductScanning,
    val currentProduct: ProductInfo? = null,
    val isLoading: Boolean = false,
    val isSyncing: Boolean = false,
    val isQrScanningActive: Boolean = false,
    val torchEnabled: Boolean = false,
    val errorMessage: String? = null,
    val lastAiResult: AiInspectionResult? = null,
    val lastHumanResult: HumanResult? = null,
    val lastSyncResult: SyncResult? = null,
    val inspectionItems: List<com.imageflow.kmp.network.InspectionItemKmp> = emptyList()
)
