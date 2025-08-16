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
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.rememberWindowState
import java.awt.Dimension
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
    val windowState = rememberWindowState(size = DpSize(1280.dp, 880.dp))
    Window(onCloseRequest = ::exitApplication, title = "ImageFlow Desktop", state = windowState) {
        // Set a reasonable minimum size to avoid layout clipping
        this.window.minimumSize = Dimension(1100, 720)
        MaterialTheme {
            Surface(modifier = Modifier.fillMaxSize()) {
                ImageFlowDesktopApp()
            }
        }
    }
}

@Composable
private fun ImageFlowDesktopApp() {
    val navStack = remember { mutableStateListOf(AppScreen.MAIN) }
    val currentScreen by remember { derivedStateOf { navStack.last() } }
    val navigateTo: (AppScreen) -> Unit = { screen ->
        if (navStack.last() != screen) navStack.add(screen)
    }
    val navigateBack: () -> Unit = {
        if (navStack.size > 1) navStack.removeLast()
    }

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
                val canGoBack = navStack.size > 1
                MobileInspectionScreen(
                    inspectionState = inspectionState,
                    currentProduct = uiState.currentProduct,
                    inspectionProgress = inspectionProgress.completionPercentage,
                    onQrScanClick = {
                        navigateTo(AppScreen.QR_SCAN)
                        viewModel.startQrScanning()
                    },
                    onSearchProductClick = {
                        navigateTo(AppScreen.PRODUCT_SEARCH)
                    },
                    onStartInspectionClick = {
                        viewModel.startInspection(InspectionType.STATIC_IMAGE)
                    },
                    onViewHistoryClick = {
                        navigateTo(AppScreen.HISTORY)
                    },
                    onSettingsClick = {
                        navigateTo(AppScreen.SETTINGS)
                    },
                    onBack = if (canGoBack) ({ navigateBack() }) else null
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
                        navigateBack()
                        viewModel.stopQrScanning()
                    },
                    onTorchToggle = {
                        viewModel.setTorchEnabled(!uiState.torchEnabled)
                    },
                    onManualEntryClick = {
                        navigateTo(AppScreen.PRODUCT_SEARCH)
                    },
                    onAcceptResult = { result ->
                        viewModel.acceptQrResult(result)
                        navigateBack()
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
                        navigateTo(AppScreen.MAIN)
                        viewModel.clearSearchResults()
                    },
                    onAdvancedSearch = { pt, mn -> viewModel.searchProductsAdvanced(pt, mn) },
                    onSelectProduct = { p ->
                        viewModel.selectProduct(p)
                        // Keep search screen in the stack so Main's back goes to search
                        navigateTo(AppScreen.MAIN)
                        viewModel.clearSearchResults()
                    },
                    onBack = {
                        viewModel.resetToScanning()
                        navigateBack()
                        viewModel.clearSearchResults()
                    }
                )
            }

            AppScreen.INSPECTION_DETAIL -> {
                ScreenWithTopBar(title = "検査詳細", onBack = { navigateBack() }) {
                    Box(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                        Text("Inspection Detail Screen - Coming Soon")
                    }
                }
            }

            AppScreen.HISTORY -> {
                ScreenWithTopBar(title = "履歴", onBack = { navigateBack() }) {
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
                    onBack = { navigateBack() }
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
