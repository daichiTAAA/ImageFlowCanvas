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
import com.imageflow.kmp.models.*
import com.imageflow.kmp.state.InspectionState
import com.imageflow.kmp.di.DependencyContainer
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
    
    MaterialTheme {
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
                    },
                    onViewHistoryClick = {
                        // TODO: Implement inspection history screen
                        currentScreen = AppScreen.HISTORY
                    },
                    onSettingsClick = {
                        // TODO: Implement settings screen
                        currentScreen = AppScreen.SETTINGS
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
                ScreenWithTopBar(title = "製品検索", onBack = { currentScreen = AppScreen.MAIN }) {
                    Box(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                        Text("Product Search Screen - Coming Soon")
                    }
                }
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
                ScreenWithTopBar(title = "設定", onBack = { currentScreen = AppScreen.MAIN }) {
                    Box(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                        Text("Settings Screen - Coming Soon")
                    }
                }
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
    
    // Simulate QR scan result for demo purposes
    LaunchedEffect(currentScreen) {
        if (currentScreen == AppScreen.QR_SCAN && uiState.isQrScanningActive) {
            kotlinx.coroutines.delay(3000) // Simulate scan delay
            
            // Simulate a successful QR scan
            val simulatedQrData = "WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1"
            viewModel.processQrScan(simulatedQrData)
        }
    }
    
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
