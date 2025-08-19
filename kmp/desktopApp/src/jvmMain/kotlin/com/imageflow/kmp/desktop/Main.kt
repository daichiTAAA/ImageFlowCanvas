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
            // Allow smaller handheld-like screens. Minimum ~360x240.
            window.minimumSize = java.awt.Dimension(360, 240)
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
                val processes by settingsVm.processes.collectAsState()
                val (grpcHost, grpcPort) = remember(baseUrl) { parseGrpcEndpoint(baseUrl) }
                // Ensure token is valid for every inspection session
                var tokenReady by remember { mutableStateOf<Boolean?>(null) }
                LaunchedEffect(processCode, baseUrl) {
                    tokenReady = null
                    val ok = try { settingsVm.ensureTokenValidForStreaming() } catch (_: Exception) { false }
                    tokenReady = ok
                }

                // Track per-item sticky OK and last OK snapshot (JPEG bytes)
                data class OkSnap(val bytes: ByteArray, val detections: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>)
                val okSnapshots = remember { mutableStateMapOf<String, OkSnap>() } // itemId -> snapshot
                data class RtFrame(val bytes: ByteArray, val dets: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>, val sj: String?)
                val realtimeByItem = remember { mutableStateMapOf<String, RtFrame>() }
                val humanDecisions = remember { mutableStateMapOf<String, com.imageflow.kmp.models.HumanResult>() }
                var currentIdx by remember(uiState.inspectionItems) { mutableStateOf(0) }
                val orderedItems = remember(uiState.inspectionItems) { uiState.inspectionItems.sortedBy { it.execution_order } }
                // Ensure currentIdx points to next item without human decision
                LaunchedEffect(humanDecisions.size, orderedItems) {
                    if (currentIdx >= orderedItems.size) return@LaunchedEffect
                    val next = orderedItems.indexOfFirst { humanDecisions[it.id] == null }
                    if (next >= 0) currentIdx = next
                }

                // Realtime preview + streaming to backend via gRPC
                Column(Modifier.fillMaxSize()) {
                    if (processCode.isNullOrBlank()) {
                        // 工程コード未設定エラー表示（ストリーミングは開始しない）
                        androidx.compose.material3.Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                androidx.compose.material3.Text(
                                    text = "工程コードが未設定です",
                                    color = androidx.compose.ui.graphics.Color.Red
                                )
                                Spacer(Modifier.height(8.dp))
                                androidx.compose.material3.Text(
                                    text = "設定画面で工程コードを選択してください。設定→工程コード。"
                                )
                                Spacer(Modifier.height(12.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    androidx.compose.material3.Button(onClick = { currentScreen = AppScreen.SETTINGS }) {
                                        androidx.compose.material3.Text("設定を開く")
                                    }
                                    androidx.compose.material3.OutlinedButton(onClick = { currentScreen = AppScreen.MAIN }) {
                                        androidx.compose.material3.Text("戻る")
                                    }
                                }
                            }
                        }
                        return@ScreenWithTopBar
                    }

                    if (tokenReady == null) {
                        // Show a small banner but keep the screen composed to avoid tearing down the stream
                        androidx.compose.material3.AssistChip(onClick = {}, label = { Text("認証確認中...") }, modifier = Modifier.padding(8.dp))
                    }
                    if (tokenReady == false) {
                        androidx.compose.material3.Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                androidx.compose.material3.Text(
                                    text = "認証が必要です",
                                    color = androidx.compose.ui.graphics.Color.Red
                                )
                                Spacer(Modifier.height(8.dp))
                                androidx.compose.material3.Text("設定画面からログインしてください。")
                                Spacer(Modifier.height(12.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    androidx.compose.material3.Button(onClick = { currentScreen = AppScreen.SETTINGS }) {
                                        androidx.compose.material3.Text("設定を開く")
                                    }
                                    androidx.compose.material3.OutlinedButton(onClick = { currentScreen = AppScreen.MAIN }) {
                                        androidx.compose.material3.Text("戻る")
                                    }
                                }
                            }
                        }
                        return@ScreenWithTopBar
                    }
                    val selectedItem = orderedItems.getOrNull(currentIdx)
                    val selectedPipelineId = selectedItem?.pipeline_id
                    val orderLabel = buildString {
                        append("項目 ")
                        append((currentIdx + 1).coerceAtMost(orderedItems.size))
                        append("/")
                        append(orderedItems.size)
                        selectedItem?.name?.let { append(" - ").append(it) }
                    }
                    androidx.compose.runtime.key(selectedItem?.id) {
                    RealtimeInspectionDesktop(
                        grpcHost = grpcHost,
                        grpcPort = grpcPort,
                        pipelineId = selectedPipelineId,
                        authToken = authToken,
                        orderLabel = orderLabel,
                        renderUi = false,
                        targetItemId = selectedItem?.id,
                        processingParams = buildMap {
                            uiState.currentProduct?.productCode?.let { put("product_code", it) }
                            processCode?.let { put("process_code", it) }
                            // Pass explicit target item id to help server-side disambiguation
                            selectedItem?.id?.let { put("target_item_id", it) }
                            // Include pipeline params from the selected item
                            (selectedItem?.pipeline_params ?: emptyMap()).forEach { (k, v) -> put(k, v) }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        onDetectionsUpdated = { det, ms ->
                            // legacy counter-only path
                            viewModel.onRealtimeAiUpdate(det, ms, selectedPipelineId)
                        },
                        onRealtimeUpdate = { det, ms, plId, details, serverJudgment ->
                            viewModel.onRealtimeAiUpdate(det, ms, plId, details, serverJudgment)
                        },
                        onOkSnapshot = { plId, jpeg, details ->
                            // Prefer explicitly selected item id; fallback to pipeline mapping only if needed
                            val itemId = selectedItem?.id ?: if (!plId.isNullOrBlank()) uiState.inspectionItems.firstOrNull { it.pipeline_id == plId }?.id else null
                            if (!itemId.isNullOrBlank()) {
                                if (humanDecisions[itemId] == null) {
                                    okSnapshots[itemId] = OkSnap(jpeg, details)
                                }
                            }
                        },
                        onPreviewFrame = { plId, jpeg, details, sj ->
                            // Prefer explicitly selected item id; fallback to pipeline mapping only if needed
                            val itemId = selectedItem?.id ?: if (!plId.isNullOrBlank()) uiState.inspectionItems.firstOrNull { it.pipeline_id == plId }?.id else null
                            if (!itemId.isNullOrBlank()) {
                                realtimeByItem[itemId] = RtFrame(jpeg, details, sj)
                            }
                        }
                    )
                    }
                    val processName = processes.firstOrNull { it.process_code == processCode }?.process_name
                    DesktopInspectionDetailPanel(
                        currentProduct = uiState.currentProduct,
                        processCode = processCode,
                        processName = processName,
                        inspectionState = inspectionState,
                        progress = if (orderedItems.isNotEmpty()) humanDecisions.size.toFloat() / orderedItems.size.toFloat() else 0f,
                        lastAiResult = uiState.lastAiResult,
                        isLoading = uiState.isLoading,
                        errorMessage = uiState.errorMessage,
                        inspectionItems = orderedItems,
                        okSnapshots = okSnapshots.mapValues { it.value.bytes to it.value.detections },
                        realtimeSnapshots = realtimeByItem.mapValues { it.value.bytes to it.value.dets to it.value.sj },
                        perItemHuman = humanDecisions,
                        currentIndex = currentIdx,
                        onSelectItemIndex = { idx ->
                            if (idx in orderedItems.indices) {
                                currentIdx = idx
                                // Clear realtime frames of other items to avoid confusion
                                val curId = orderedItems[idx].id
                                realtimeByItem.keys.toList().forEach { k -> if (k != curId) realtimeByItem.remove(k) }
                            }
                        },
                        onItemHumanReview = { itemId, result ->
                            humanDecisions[itemId] = result
                            // If current item was confirmed, advance to next
                            val idx = orderedItems.indexOfFirst { it.id == itemId }
                            if (idx >= 0 && idx == currentIdx) {
                                val next = orderedItems.indexOfFirst { humanDecisions[it.id] == null }
                                if (next >= 0) {
                                    currentIdx = next
                                    val curId = orderedItems[next].id
                                    realtimeByItem.keys.toList().forEach { k -> if (k != curId) realtimeByItem.remove(k) }
                                }
                            }
                        },
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
