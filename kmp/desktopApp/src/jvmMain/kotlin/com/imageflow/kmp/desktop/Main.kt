package com.imageflow.kmp.desktop

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.rememberWindowState
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.application
import com.imageflow.kmp.di.DependencyContainer
import com.imageflow.kmp.models.InspectionType
import com.imageflow.kmp.ui.mobile.InspectionDetailScreen
import com.imageflow.kmp.ui.mobile.MobileInspectionScreen
import com.imageflow.kmp.ui.mobile.ProductSearchScreen
import com.imageflow.kmp.ui.mobile.SettingsScreen

fun main() = application {
    val windowState = rememberWindowState(width = 1280.dp, height = 880.dp)
    Window(onCloseRequest = ::exitApplication, title = "ImageFlow Desktop", state = windowState) {
        // Enforce a reasonable minimum window size
        LaunchedEffect(Unit) {
            window.minimumSize = java.awt.Dimension(1100, 720)
        }
        MaterialTheme {
            ImageFlowDesktopApp()
        }
    }
}

@Composable
private fun ImageFlowDesktopApp() {
    var currentScreen by remember { mutableStateOf(AppScreen.MAIN) }

    val viewModel = remember {
        DependencyContainer.createMobileInspectionViewModel(
            kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main)
        )
    }

    val uiState by viewModel.uiState.collectAsState()
    val qrScanResult by viewModel.qrScanResult.collectAsState()
    val inspectionState by viewModel.inspectionState.collectAsState()
    val inspectionProgress by viewModel.inspectionProgress.collectAsState()
    val suggestions by viewModel.suggestions.collectAsState()
    val searchResults by viewModel.searchResults.collectAsState()

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
                    currentScreen = AppScreen.PRODUCT_SEARCH
                },
                onStartInspectionClick = {
                    viewModel.startInspection(InspectionType.STATIC_IMAGE)
                    currentScreen = AppScreen.INSPECTION_DETAIL
                },
                onViewHistoryClick = {
                    currentScreen = AppScreen.HISTORY
                },
                onSettingsClick = {
                    currentScreen = AppScreen.SETTINGS
                },
                onBack = {
                    currentScreen = AppScreen.PRODUCT_SEARCH
                }
            )
        }

        AppScreen.QR_SCAN -> {
            QrScanningScreenDesktop(
                isScanning = uiState.isQrScanningActive,
                lastScanResult = qrScanResult,
                onBackClick = {
                    currentScreen = AppScreen.MAIN
                    viewModel.stopQrScanning()
                },
                onManualEntryClick = {
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
            val settingsVm = remember { com.imageflow.kmp.ui.viewmodel.SettingsViewModel() }
            val currentUrl by settingsVm.baseUrl.collectAsState()
            SettingsScreen(
                initialBaseUrl = currentUrl,
                onApply = { newUrl ->
                    settingsVm.setBaseUrl(newUrl)
                    settingsVm.apply()
                },
                onTest = { newUrl ->
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
    ) {
        Box(modifier = Modifier.fillMaxSize().padding(it)) {
            content()
        }
    }
}

private enum class AppScreen {
    MAIN,
    QR_SCAN,
    PRODUCT_SEARCH,
    INSPECTION_DETAIL,
    HISTORY,
    SETTINGS
}
