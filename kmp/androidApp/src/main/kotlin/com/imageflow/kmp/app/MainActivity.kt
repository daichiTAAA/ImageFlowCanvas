package com.imageflow.kmp.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.imageflow.kmp.database.AndroidDbContextHolder
import com.imageflow.kmp.ui.mobile.MobileInspectionScreen
import com.imageflow.kmp.ui.mobile.QrScanningScreen
import com.imageflow.kmp.models.*
import com.imageflow.kmp.state.InspectionState

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
    var inspectionState by remember { mutableStateOf(InspectionState.ProductScanning) }
    var currentProduct by remember { mutableStateOf<ProductInfo?>(null) }
    var qrScanResult by remember { mutableStateOf<QrScanResult?>(null) }
    
    MaterialTheme {
        when (currentScreen) {
            AppScreen.MAIN -> {
                MobileInspectionScreen(
                    inspectionState = inspectionState,
                    currentProduct = currentProduct,
                    onQrScanClick = {
                        currentScreen = AppScreen.QR_SCAN
                    },
                    onSearchProductClick = {
                        // TODO: Implement product search screen
                    },
                    onStartInspectionClick = {
                        if (currentProduct != null) {
                            inspectionState = InspectionState.InProgress
                            // TODO: Start actual inspection workflow
                        }
                    },
                    onViewHistoryClick = {
                        // TODO: Implement inspection history screen
                    },
                    onSettingsClick = {
                        // TODO: Implement settings screen
                    }
                )
            }
            
            AppScreen.QR_SCAN -> {
                QrScanningScreen(
                    isScanning = true,
                    lastScanResult = qrScanResult,
                    onBackClick = {
                        currentScreen = AppScreen.MAIN
                        qrScanResult = null
                    },
                    onAcceptResult = { result ->
                        if (result.success && result.productInfo != null) {
                            currentProduct = result.productInfo
                            inspectionState = InspectionState.ProductIdentified
                            currentScreen = AppScreen.MAIN
                        }
                    },
                    onRetryClick = {
                        qrScanResult = null
                        // Restart scanning
                    },
                    onTorchToggle = {
                        // TODO: Implement torch toggle
                    },
                    onManualEntryClick = {
                        // TODO: Implement manual product entry
                    }
                )
            }
        }
    }
    
    // Simulate QR scan result for demo
    LaunchedEffect(currentScreen) {
        if (currentScreen == AppScreen.QR_SCAN) {
            kotlinx.coroutines.delay(3000) // Simulate scan delay
            qrScanResult = QrScanResult(
                success = true,
                productInfo = ProductInfo(
                    workOrderId = "WORK001",
                    instructionId = "INST001",
                    productType = "TYPE-A",
                    machineNumber = "MACHINE-123",
                    productionDate = "2024-01-15",
                    monthlySequence = 1
                ).let { it.copy(id = it.generateId()) },
                rawData = "WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1",
                scanType = ScanType.QR_CODE,
                confidence = 0.95f,
                validationStatus = ValidationStatus.VALID
            )
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
