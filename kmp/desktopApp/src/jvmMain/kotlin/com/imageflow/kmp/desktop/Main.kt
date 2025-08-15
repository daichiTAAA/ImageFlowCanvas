package com.imageflow.kmp.desktop

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import com.imageflow.kmp.di.DependencyContainer
import com.imageflow.kmp.models.InspectionType
import com.imageflow.kmp.state.InspectionState
import com.imageflow.kmp.ui.mobile.MobileInspectionScreen
import com.imageflow.kmp.ui.mobile.ProductSearchScreen
import com.imageflow.kmp.ui.mobile.QrScanningScreen
import com.imageflow.kmp.ui.mobile.SettingsScreen
import com.imageflow.kmp.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay

fun main() = application {
    Window(onCloseRequest = ::exitApplication, title = "ImageFlow Desktop") {
        MaterialTheme {
            Surface(modifier = Modifier.fillMaxSize()) {
                ImageFlowDesktopApp()
            }
        }
    }
}

@Composable
private fun ImageFlowDesktopApp() {
    var currentScreen by remember { mutableStateOf(AppScreen.MAIN) }

    // Create ViewModel instance using dependency injection
    val viewModel = remember {
        DependencyContainer.createMobileInspectionViewModel(
            CoroutineScope(Dispatchers.Default)
        )
    }

    // Observe ViewModel state
    val uiState by viewModel.uiState.collectAsState()
    val qrScanResult by viewModel.qrScanResult.collectAsState()
    val inspectionState by viewModel.inspectionState.collectAsState()
    val inspectionProgress by viewModel.inspectionProgress.collectAsState()
    val suggestions by viewModel.suggestions.collectAsState()
    val searchResults by viewModel.searchResults.collectAsState()

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
                        currentScreen = AppScreen.PRODUCT_SEARCH
                    },
                    onStartInspectionClick = {
                        viewModel.startInspection(InspectionType.STATIC_IMAGE)
                    },
                    onViewHistoryClick = {
                        currentScreen = AppScreen.HISTORY
                    },
                    onSettingsClick = {
                        currentScreen = AppScreen.SETTINGS
                    }
                )

                // Show error in logs for now
                uiState.errorMessage?.let { errorMessage ->
                    LaunchedEffect(errorMessage) {
                        println("Error: $errorMessage")
                        viewModel.clearErrorMessage()
                    }
                }
            }

            AppScreen.QR_SCAN -> {
                // Use shared placeholder QR scanning UI for desktop
                QrScanningScreen(
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
                        currentScreen = AppScreen.PRODUCT_SEARCH
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
                    Box(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                        Text("Inspection Detail Screen - Coming Soon")
                    }
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
                    onTest = { settingsVm.testConnection() },
                    onDiagnose = { newUrl -> settingsVm.diagnose(newUrl) },
                    onResetDefault = { settingsVm.resetToDefault() },
                    onBack = { currentScreen = AppScreen.MAIN }
                )
            }
        }
    }

    // Simulate QR scan result like Android demo
    LaunchedEffect(currentScreen, uiState.isQrScanningActive) {
        if (currentScreen == AppScreen.QR_SCAN && uiState.isQrScanningActive) {
            delay(3000)
            val simulatedQrData = "WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1"
            viewModel.processQrScan(simulatedQrData)
        }
    }

    // Show loading indicator
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

private enum class AppScreen {
    MAIN,
    QR_SCAN,
    PRODUCT_SEARCH,
    INSPECTION_DETAIL,
    HISTORY,
    SETTINGS
}
