package com.imageflow.kmp.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.BackHandler
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.imageflow.kmp.database.AndroidDbContextHolder
import com.imageflow.kmp.ui.mobile.MobileInspectionScreen
import com.imageflow.kmp.ui.mobile.QrScanningScreen
import com.imageflow.kmp.ui.mobile.InspectionDetailScreen
import com.imageflow.kmp.models.HumanResult
import com.imageflow.kmp.ui.mobile.ProductSearchScreen
import com.imageflow.kmp.models.*
import com.imageflow.kmp.state.InspectionState
import com.imageflow.kmp.di.DependencyContainer
import com.imageflow.kmp.ui.mobile.SettingsScreen
import com.imageflow.kmp.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize SQLDelight Android driver context
        AndroidDbContextHolder.context = applicationContext

        setContent {
            ImageFlowMobileApp()
        }
    }
}

@Composable
fun ImageFlowMobileApp() {
    var currentScreen by remember { mutableStateOf(AppScreen.MAIN) }
    
    // Create ViewModel instance using dependency injection
    val viewModel = remember { 
        DependencyContainer.createMobileInspectionViewModel(
            // In real app, would use proper ViewModel scope
            kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main)
        )
    }
    
    // Observe ViewModel state
    val uiState by viewModel.uiState.collectAsState()
    val qrScanResult by viewModel.qrScanResult.collectAsState()
    val inspectionState by viewModel.inspectionState.collectAsState()
    val inspectionProgress by viewModel.inspectionProgress.collectAsState()
    val suggestions by viewModel.suggestions.collectAsState()
    val searchResults by viewModel.searchResults.collectAsState()
    val productStatuses by viewModel.productStatuses.collectAsState()
    val currentInspection by viewModel.currentInspection.collectAsState()
    
    MaterialTheme {
        val settingsVm = remember { SettingsViewModel() }
        when (currentScreen) {
            AppScreen.MAIN -> {
                MobileInspectionScreen(
                    inspectionState = inspectionState,
                    currentProduct = uiState.currentProduct,
                    inspectionProgress = inspectionProgress.completionPercentage,
                    onQrScanClick = {
                        currentScreen = AppScreen.QR_SCAN
                        viewModel.startQrScanning()
                    },
                    onSearchProductClick = {
                        // TODO: Implement product search screen
                        currentScreen = AppScreen.PRODUCT_SEARCH
                    },
                    onStartInspectionClick = {
                        viewModel.startInspection(InspectionType.STATIC_IMAGE)
                        currentScreen = AppScreen.INSPECTION_DETAIL
                    },
                    onOpenInspectionDetail = {
                        currentScreen = AppScreen.INSPECTION_DETAIL
                    },
                    onViewHistoryClick = {
                        // TODO: Implement inspection history screen
                        currentScreen = AppScreen.HISTORY
                    },
                    onSettingsClick = {
                        // TODO: Implement settings screen
                        currentScreen = AppScreen.SETTINGS
                    },
                    onBack = {
                        currentScreen = AppScreen.PRODUCT_SEARCH
                    }
                )
                
                // Show error snackbar if there's an error
                uiState.errorMessage?.let { errorMessage ->
                    LaunchedEffect(errorMessage) {
                        // In real app, would show Snackbar
                        println("Error: $errorMessage")
                        viewModel.clearErrorMessage()
                    }
                }
            }
            
            AppScreen.QR_SCAN -> {
                QrScanningScreenAndroid(
                    isScanning = uiState.isQrScanningActive,
                    torchEnabled = uiState.torchEnabled,
                    lastScanResult = qrScanResult,
                    onBackClick = {
                        currentScreen = AppScreen.MAIN
                        viewModel.stopQrScanning()
                    },
                    onTorchToggle = {
                        viewModel.setTorchEnabled(!uiState.torchEnabled)
                    },
                    onManualEntryClick = {
                        // TODO: Manual input
                        currentScreen = AppScreen.PRODUCT_SEARCH
                    },
                    onRawScanned = { raw ->
                        viewModel.processQrScan(raw)
                    },
                    onAcceptResult = { result ->
                        viewModel.acceptQrResult(result)
                        currentScreen = AppScreen.MAIN
                    },
                    onRetryClick = {
                        viewModel.retryQrScan()
                    }
                )
            }
            
            AppScreen.PRODUCT_SEARCH -> {
                ProductSearchScreen(
                    isLoading = uiState.isLoading,
                    suggestions = suggestions,
                    searchResults = searchResults?.products ?: emptyList(),
                    inspectionStatuses = productStatuses,
                    onQueryChange = { q -> viewModel.loadSuggestions(q) },
                    onSearch = { q -> viewModel.searchProducts(q) },
                    onSelectSuggestion = { s ->
                        viewModel.selectProductById(s.productId)
                        currentScreen = AppScreen.MAIN
                        viewModel.clearSearchResults()
                    },
                    onAdvancedSearch = { pt, mn -> viewModel.searchProductsAdvanced(pt, mn) },
                    onSelectProduct = { p ->
                        viewModel.selectProduct(p)
                        currentScreen = AppScreen.MAIN
                        viewModel.clearSearchResults()
                    },
                    onBack = {
                        currentScreen = AppScreen.MAIN
                        viewModel.clearSearchResults()
                    }
                )
            }
            
            AppScreen.INSPECTION_DETAIL -> {
                ScreenWithTopBar(title = "検査詳細", onBack = { currentScreen = AppScreen.MAIN }) {
                    InspectionDetailScreen(
                        currentProduct = uiState.currentProduct,
                        inspectionState = inspectionState,
                        progress = inspectionProgress.completionPercentage,
                        lastAiResult = uiState.lastAiResult,
                        isLoading = uiState.isLoading,
                        errorMessage = uiState.errorMessage,
                        addedImages = currentInspection?.imagePaths ?: emptyList(),
                        onAddImage = { path -> viewModel.captureImage(path) },
                        onRunAi = { viewModel.processAiInspection() },
                        onHumanReview = { result -> viewModel.submitHumanReview(result) },
                        onBack = { currentScreen = AppScreen.MAIN }
                    )
                }
            }
            
            AppScreen.HISTORY -> {
                ScreenWithTopBar(title = "履歴", onBack = { currentScreen = AppScreen.MAIN }) {
                    Box(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                        Text("History Screen - Coming Soon")
                    }
                }
            }
            
            AppScreen.SETTINGS -> {
                val currentUrl by settingsVm.baseUrl.collectAsState()
                SettingsScreen(
                    initialBaseUrl = currentUrl,
                    onApply = { newUrl ->
                        settingsVm.setBaseUrl(newUrl)
                        settingsVm.apply()
                    },
                    onTest = { newUrl ->
                        // Temporarily apply and test
                        settingsVm.setBaseUrl(newUrl)
                        settingsVm.apply()
                        settingsVm.testConnection()
                    },
                    onDiagnose = { newUrl ->
                        settingsVm.diagnose(newUrl)
                    },
                    onResetDefault = {
                        settingsVm.resetToDefault()
                    },
                    onBack = { currentScreen = AppScreen.MAIN }
                )
            }
        }
    }

    // Handle system back press to navigate within app
    BackHandler(enabled = currentScreen != AppScreen.MAIN) {
        if (currentScreen == AppScreen.QR_SCAN) {
            viewModel.stopQrScanning()
        }
        currentScreen = AppScreen.MAIN
    }
    
    // Removed simulated QR success; use real scanner on Android
    
    // Handle loading states
    if (uiState.isLoading) {
        Box(modifier = Modifier.fillMaxSize()) {
            CircularProgressIndicator()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ScreenWithTopBar(
    title: String,
    onBack: () -> Unit,
    content: @Composable () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "戻る"
                        )
                    }
                }
            )
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            content()
        }
    }
}

enum class AppScreen {
    MAIN,
    QR_SCAN,
    PRODUCT_SEARCH,
    INSPECTION_DETAIL,
    HISTORY,
    SETTINGS
}
