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
import java.awt.FileDialog
import java.awt.Frame
import com.imageflow.kmp.ui.mobile.MobileInspectionScreen
import com.imageflow.kmp.ui.mobile.ProductSearchScreen
import com.imageflow.kmp.ui.mobile.SettingsScreen
import com.imageflow.kmp.ui.viewmodel.SettingsViewModel

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
    val currentInspection by viewModel.currentInspection.collectAsState()
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
                val settingsVm = remember { SettingsViewModel() }
                val baseUrl by settingsVm.baseUrl.collectAsState()
                val (grpcHost, grpcPort) = remember(baseUrl) { parseGrpcEndpoint(baseUrl) }
                // Realtime preview + streaming to backend via gRPC
                Column(Modifier.fillMaxSize()) {
                    RealtimeInspectionDesktop(grpcHost = grpcHost, grpcPort = grpcPort, modifier = Modifier.fillMaxWidth())
                InspectionDetailScreen(
                    currentProduct = uiState.currentProduct,
                    inspectionState = inspectionState,
                    progress = inspectionProgress.completionPercentage,
                    lastAiResult = uiState.lastAiResult,
                    isLoading = uiState.isLoading,
                    errorMessage = uiState.errorMessage,
                    addedImages = currentInspection?.imagePaths ?: emptyList(),
                    onAddImage = { _ ->
                        pickImageFile()?.let { selected ->
                            viewModel.captureImage(selected)
                        }
                    },
                    onRunAi = { viewModel.processAiInspection() },
                    onHumanReview = { result -> viewModel.submitHumanReview(result) },
                    onBack = { currentScreen = AppScreen.MAIN }
                )
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

// Simple native file picker for images (macOS/Windows/Linux)
private fun pickImageFile(): String? {
    return try {
        val dialog = FileDialog(null as Frame?, "画像を選択", FileDialog.LOAD)
        dialog.isMultipleMode = false
        dialog.setFilenameFilter { _, name ->
            val lower = name.lowercase()
            lower.endsWith(".jpg") || lower.endsWith(".jpeg") || lower.endsWith(".png") || lower.endsWith(".bmp") || lower.endsWith(".webp")
        }
        dialog.isVisible = true
        val file = dialog.files?.firstOrNull()
        file?.absolutePath
    } catch (_: Throwable) {
        null
    }
}

private fun parseGrpcEndpoint(baseUrl: String?): Pair<String, Int> {
    return try {
        val url = java.net.URI(baseUrl ?: "http://127.0.0.1:8000")
        val host = url.host ?: "127.0.0.1"
        val port = if (url.port != -1) url.port else 50051
        host to port
    } catch (_: Throwable) {
        "127.0.0.1" to 50051
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
