package com.imageflow.kmp.ui.mobile

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.imageflow.kmp.models.*

// QR scanning screen based on F-021-1 QR code information acquisition requirements
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun QrScanningScreen(
    isScanning: Boolean = true,
    torchEnabled: Boolean = false,
    lastScanResult: QrScanResult? = null,
    onBackClick: () -> Unit = {},
    onTorchToggle: () -> Unit = {},
    onManualEntryClick: () -> Unit = {},
    onAcceptResult: (QrScanResult) -> Unit = {},
    onRetryClick: () -> Unit = {}
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Top bar
        QrScanTopBar(
            torchEnabled = torchEnabled,
            onBackClick = onBackClick,
            onTorchToggle = onTorchToggle,
            onManualEntryClick = onManualEntryClick
        )
        
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            // Camera preview placeholder (would be actual camera in real implementation)
            CameraPreviewPlaceholder()
            
            // Scanning overlay
            QrScanningOverlay(isScanning = isScanning)
            
            // Scanning instructions
            QrScanningInstructions(
                modifier = Modifier.align(Alignment.BottomCenter)
            )
        }
        
        // Bottom result area
        lastScanResult?.let { result ->
            QrScanResultCard(
                result = result,
                onAccept = { onAcceptResult(result) },
                onRetry = onRetryClick
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun QrScanTopBar(
    torchEnabled: Boolean,
    onBackClick: () -> Unit,
    onTorchToggle: () -> Unit,
    onManualEntryClick: () -> Unit
) {
    TopAppBar(
        title = {
            Text(
                text = "QRコードスキャン",
                color = Color.White
            )
        },
        navigationIcon = {
            IconButton(onClick = onBackClick) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "戻る",
                    tint = Color.White
                )
            }
        },
        actions = {
            // Manual entry button
            IconButton(onClick = onManualEntryClick) {
                Icon(
                    imageVector = Icons.Default.Keyboard,
                    contentDescription = "手動入力",
                    tint = Color.White
                )
            }
            
            // Torch toggle button
            IconButton(onClick = onTorchToggle) {
                Icon(
                    imageVector = if (torchEnabled) Icons.Default.FlashlightOff else Icons.Default.FlashlightOn,
                    contentDescription = if (torchEnabled) "ライトOFF" else "ライトON",
                    tint = if (torchEnabled) Color.Yellow else Color.White
                )
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = Color.Black.copy(alpha = 0.7f)
        )
    )
}

@Composable
private fun CameraPreviewPlaceholder() {
    // This would be replaced with actual camera preview
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Gray),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Default.CameraAlt,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(64.dp)
            )
            Text(
                text = "カメラプレビュー",
                color = Color.White,
                fontSize = 16.sp
            )
        }
    }
}

@Composable
private fun QrScanningOverlay(
    isScanning: Boolean
) {
    val density = LocalDensity.current
    
    Canvas(
        modifier = Modifier.fillMaxSize()
    ) {
        val canvasWidth = size.width
        val canvasHeight = size.height
        
        // QR scanning frame
        val frameSize = with(density) { 250.dp.toPx() }
        val frameLeft = (canvasWidth - frameSize) / 2
        val frameTop = (canvasHeight - frameSize) / 2
        
        // Dark overlay outside scanning area
        drawRect(
            color = Color.Black.copy(alpha = 0.5f),
            topLeft = Offset(0f, 0f),
            size = Size(canvasWidth, frameTop)
        )
        drawRect(
            color = Color.Black.copy(alpha = 0.5f),
            topLeft = Offset(0f, frameTop + frameSize),
            size = Size(canvasWidth, canvasHeight - frameTop - frameSize)
        )
        drawRect(
            color = Color.Black.copy(alpha = 0.5f),
            topLeft = Offset(0f, frameTop),
            size = Size(frameLeft, frameSize)
        )
        drawRect(
            color = Color.Black.copy(alpha = 0.5f),
            topLeft = Offset(frameLeft + frameSize, frameTop),
            size = Size(canvasWidth - frameLeft - frameSize, frameSize)
        )
        
        // Scanning frame
        val frameColor = if (isScanning) Color.Green else Color.White
        val strokeWidth = with(density) { 3.dp.toPx() }
        val cornerLength = with(density) { 20.dp.toPx() }
        
        // Draw corner indicators
        // Top-left corner
        drawLine(
            color = frameColor,
            start = Offset(frameLeft, frameTop),
            end = Offset(frameLeft + cornerLength, frameTop),
            strokeWidth = strokeWidth
        )
        drawLine(
            color = frameColor,
            start = Offset(frameLeft, frameTop),
            end = Offset(frameLeft, frameTop + cornerLength),
            strokeWidth = strokeWidth
        )
        
        // Top-right corner
        drawLine(
            color = frameColor,
            start = Offset(frameLeft + frameSize, frameTop),
            end = Offset(frameLeft + frameSize - cornerLength, frameTop),
            strokeWidth = strokeWidth
        )
        drawLine(
            color = frameColor,
            start = Offset(frameLeft + frameSize, frameTop),
            end = Offset(frameLeft + frameSize, frameTop + cornerLength),
            strokeWidth = strokeWidth
        )
        
        // Bottom-left corner
        drawLine(
            color = frameColor,
            start = Offset(frameLeft, frameTop + frameSize),
            end = Offset(frameLeft + cornerLength, frameTop + frameSize),
            strokeWidth = strokeWidth
        )
        drawLine(
            color = frameColor,
            start = Offset(frameLeft, frameTop + frameSize),
            end = Offset(frameLeft, frameTop + frameSize - cornerLength),
            strokeWidth = strokeWidth
        )
        
        // Bottom-right corner
        drawLine(
            color = frameColor,
            start = Offset(frameLeft + frameSize, frameTop + frameSize),
            end = Offset(frameLeft + frameSize - cornerLength, frameTop + frameSize),
            strokeWidth = strokeWidth
        )
        drawLine(
            color = frameColor,
            start = Offset(frameLeft + frameSize, frameTop + frameSize),
            end = Offset(frameLeft + frameSize, frameTop + frameSize - cornerLength),
            strokeWidth = strokeWidth
        )
        
        // Scanning line animation (simplified)
        if (isScanning) {
            val scanLineY = frameTop + frameSize * 0.5f // Simplified - in real app, animate this
            drawLine(
                color = frameColor.copy(alpha = 0.8f),
                start = Offset(frameLeft, scanLineY),
                end = Offset(frameLeft + frameSize, scanLineY),
                strokeWidth = strokeWidth * 0.5f
            )
        }
    }
}

@Composable
private fun QrScanningInstructions(
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color.Black.copy(alpha = 0.7f)
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "QRコードをフレーム内に配置してください",
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "自動的に読み取りを開始します",
                color = Color.White.copy(alpha = 0.8f),
                fontSize = 14.sp,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun QrScanResultCard(
    result: QrScanResult,
    onAccept: () -> Unit,
    onRetry: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = if (result.success) Icons.Default.CheckCircle else Icons.Default.Error,
                    contentDescription = null,
                    tint = if (result.success) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (result.success) "QRコード読み取り成功" else "読み取りエラー",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                    color = if (result.success) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            if (result.success && result.productInfo != null) {
                // Show product information
                ProductInfoDisplay(productInfo = result.productInfo)
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = onRetry,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("再スキャン")
                    }
                    
                    Button(
                        onClick = onAccept,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("この製品を選択")
                    }
                }
            } else {
                // Show error information
                Text(
                    text = result.errorMessage ?: "QRコードを正しく読み取れませんでした",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Button(
                    onClick = onRetry,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("再試行")
                }
            }
        }
    }
}

@Composable
private fun ProductInfoDisplay(productInfo: ProductInfo) {
    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        ProductInfoRow("製品タイプ", productInfo.productType)
        ProductInfoRow("機番", productInfo.machineNumber)
        ProductInfoRow("指図番号", productInfo.workOrderId)
        ProductInfoRow("指示番号", productInfo.instructionId)
        ProductInfoRow("生産年月日", productInfo.productionDate)
        ProductInfoRow("月連番", productInfo.monthlySequence.toString())
    }
}

@Composable
private fun ProductInfoRow(
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            text = "$label:",
            fontSize = 14.sp,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.width(80.dp)
        )
        Text(
            text = value,
            fontSize = 14.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}