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
import androidx.compose.ui.window.application
import com.imageflow.kmp.di.DependencyContainer
import com.imageflow.kmp.models.InspectionType
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
                    // Use REALTIME to avoid REST orchestration; stream via gRPC instead
                    viewModel.startInspection(InspectionType.REALTIME)
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
                val authToken by settingsVm.authToken.collectAsState()
                val processCode by settingsVm.processCode.collectAsState()
                val (grpcHost, grpcPort) = remember(baseUrl) { parseGrpcEndpoint(baseUrl) }
                // Realtime preview + streaming to backend via gRPC
                Column(Modifier.fillMaxSize()) {
                    // Pick pipeline from inspection items: first by execution_order that has pipeline_id
                    val selectedPipelineId = remember(uiState.inspectionItems) {
                        uiState.inspectionItems
                            .sortedBy { it.execution_order }
                            .firstOrNull { !it.pipeline_id.isNullOrBlank() }
                            ?.pipeline_id
                    }
                    val selectedPipelineParams = remember(uiState.inspectionItems) {
                        uiState.inspectionItems
                            .sortedBy { it.execution_order }
                            .firstOrNull { !it.pipeline_id.isNullOrBlank() }
                            ?.pipeline_params ?: emptyMap()
                    }
                    RealtimeInspectionDesktop(
                        grpcHost = grpcHost,
                        grpcPort = grpcPort,
                        pipelineId = selectedPipelineId,
                        authToken = authToken,
                        processingParams = buildMap {
                            uiState.currentProduct?.productCode?.let { put("product_code", it) }
                            processCode?.let { put("process_code", it) }
                            // Include pipeline params from the selected item
                            selectedPipelineParams.forEach { (k, v) -> put(k, v) }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        onDetectionsUpdated = { det, ms ->
                            viewModel.onRealtimeAiUpdate(det, ms)
                        }
                    )
                    DesktopInspectionDetailPanel(
                        currentProduct = uiState.currentProduct,
                        inspectionState = inspectionState,
                        progress = inspectionProgress.completionPercentage,
                        lastAiResult = uiState.lastAiResult,
                        isLoading = uiState.isLoading,
                        errorMessage = uiState.errorMessage,
                        inspectionItems = uiState.inspectionItems,
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
            val currentProcess by settingsVm.processCode.collectAsState()
            val authToken by settingsVm.authToken.collectAsState()
            val processList by settingsVm.processes.collectAsState()
            SettingsScreen(
                initialBaseUrl = currentUrl,
                initialProcessCode = currentProcess,
                isAuthenticated = !authToken.isNullOrBlank(),
                onApply = { newUrl, newProcess ->
                    settingsVm.setBaseUrl(newUrl)
                    settingsVm.setProcessCode(newProcess)
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
                onLogin = { u, p ->
                    settingsVm.login(u, p)
                },
                onLogout = {
                    settingsVm.logout()
                },
                processCandidates = processList,
                onLoadProcesses = {
                    settingsVm.loadProcesses()
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
        // Always use dedicated gRPC port unless explicitly overridden via env
        val envPort = System.getenv("IFC_GRPC_PORT")?.toIntOrNull()
        val port = envPort ?: 50051
        host to port
    } catch (_: Throwable) {
        val envPort = System.getenv("IFC_GRPC_PORT")?.toIntOrNull() ?: 50051
        "127.0.0.1" to envPort
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
