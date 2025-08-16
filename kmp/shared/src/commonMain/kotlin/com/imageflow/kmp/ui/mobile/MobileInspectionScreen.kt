package com.imageflow.kmp.ui.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.imageflow.kmp.models.*
import com.imageflow.kmp.state.InspectionState

// Mobile inspection main screen based on F-021 mobile inspection app requirements
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MobileInspectionScreen(
    inspectionState: InspectionState = InspectionState.ProductScanning,
    currentProduct: ProductInfo? = null,
    inspectionProgress: Float = 0f,
    recentInspections: List<Inspection> = emptyList(),
    onQrScanClick: () -> Unit = {},
    onSearchProductClick: () -> Unit = {},
    onStartInspectionClick: () -> Unit = {},
    onViewHistoryClick: () -> Unit = {},
    onSettingsClick: () -> Unit = {},
    onBack: (() -> Unit)? = null
) {
    Scaffold(
        topBar = {
            if (onBack != null && currentProduct != null) {
                TopAppBar(
                    title = { Text("検査") },
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
        },
        bottomBar = {
            BottomActionBar(onSettingsClick = onSettingsClick)
        }
    ) { innerPadding ->
        val scrollState = rememberScrollState()
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
        // Header with app title and status
        InspectionHeader(
            inspectionState = inspectionState,
            currentProduct = currentProduct
        )
        
        // Current inspection progress (if in progress)
        if (inspectionState != InspectionState.ProductScanning && 
            inspectionState != InspectionState.Completed) {
            InspectionProgressCard(
                inspectionState = inspectionState,
                progress = inspectionProgress,
                currentProduct = currentProduct
            )
        }
        
        // Main action buttons
        QuickActionButtons(
            inspectionState = inspectionState,
            onQrScanClick = onQrScanClick,
            onSearchProductClick = onSearchProductClick,
            onStartInspectionClick = onStartInspectionClick
        )

        // Recent inspections (show only when available to save vertical space)
        if (recentInspections.isNotEmpty()) {
            RecentInspectionsSection(
                inspections = recentInspections,
                onViewHistoryClick = onViewHistoryClick
            )
        }
        
        // bottomBar handles settings button; no spacer needed when scrollable
        }
    }
}

@Composable
private fun InspectionHeader(
    inspectionState: InspectionState,
    currentProduct: ProductInfo?
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "ImageFlow 検査アプリ",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                StatusIndicator(inspectionState)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = getStateDisplayText(inspectionState),
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            // Current product info if available
            currentProduct?.let { product ->
                Spacer(modifier = Modifier.height(8.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp)
                    ) {
                        Text(
                            text = "選択中の順序情報",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            text = "${product.productCode} - ${product.machineNumber}",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "指図: ${product.workOrderId}",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusIndicator(state: InspectionState) {
    val (icon, color) = when (state) {
        is InspectionState.ProductScanning -> Icons.Default.QrCodeScanner to MaterialTheme.colorScheme.primary
        is InspectionState.ProductIdentified -> Icons.Default.CheckCircle to MaterialTheme.colorScheme.primary
        is InspectionState.InProgress -> Icons.Default.PlayArrow to MaterialTheme.colorScheme.secondary
        is InspectionState.AiCompleted -> Icons.Default.Psychology to MaterialTheme.colorScheme.tertiary
        is InspectionState.HumanReview -> Icons.Default.Visibility to MaterialTheme.colorScheme.secondary
        is InspectionState.Completed -> Icons.Default.TaskAlt to MaterialTheme.colorScheme.primary
        else -> Icons.Default.Error to MaterialTheme.colorScheme.error
    }
    
    Icon(
        imageVector = icon,
        contentDescription = null,
        tint = color,
        modifier = Modifier.size(20.dp)
    )
}

@Composable
private fun InspectionProgressCard(
    inspectionState: InspectionState,
    progress: Float,
    currentProduct: ProductInfo?
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "検査進行状況",
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            LinearProgressIndicator(
                progress = progress,
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primary
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "${(progress * 100).toInt()}% 完了",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun QuickActionButtons(
    inspectionState: InspectionState,
    onQrScanClick: () -> Unit,
    onSearchProductClick: () -> Unit,
    onStartInspectionClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "クイックアクション",
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.padding(bottom = 12.dp)
            )
            
            if (inspectionState == InspectionState.ProductScanning) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // QR Scan Button
                    QuickActionButton(
                        modifier = Modifier.weight(1f),
                        icon = Icons.Default.QrCodeScanner,
                        text = "QRスキャン",
                        enabled = true,
                        onClick = onQrScanClick
                    )

                    // Search Product Button
                    QuickActionButton(
                        modifier = Modifier.weight(1f),
                        icon = Icons.Default.Search,
                        text = "順序情報取得",
                        enabled = true,
                        onClick = onSearchProductClick
                    )
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    QuickActionButton(
                        modifier = Modifier.weight(1f),
                        icon = Icons.Default.Search,
                        text = "順序情報を変更",
                        enabled = true,
                        onClick = onSearchProductClick
                    )
                    QuickActionButton(
                        modifier = Modifier.weight(1f),
                        icon = Icons.Default.QrCodeScanner,
                        text = "QR再スキャン",
                        enabled = true,
                        onClick = onQrScanClick
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            if (inspectionState == InspectionState.ProductIdentified) {
                // Start Inspection Button
                Button(
                    onClick = onStartInspectionClick,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("検査開始")
                }
            }
        }
    }
}

@Composable
private fun QuickActionButton(
    modifier: Modifier = Modifier,
    icon: ImageVector,
    text: String,
    enabled: Boolean = true,
    onClick: () -> Unit
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = text,
                fontSize = 12.sp
            )
        }
    }
}

@Composable
private fun RecentInspectionsSection(
    inspections: List<Inspection>,
    onViewHistoryClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "最近の検査",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium
                )
                
                TextButton(onClick = onViewHistoryClick) {
                    Text("すべて表示")
                    Icon(
                        imageVector = Icons.Default.ArrowForward,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
            
            if (inspections.isEmpty()) {
                Text(
                    text = "検査履歴がありません",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 16.dp)
                )
            } else {
                LazyColumn(
                    modifier = Modifier.height(200.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(inspections.take(5)) { inspection ->
                        InspectionListItem(inspection = inspection)
                    }
                }
            }
        }
    }
}

@Composable
private fun InspectionListItem(inspection: Inspection) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        StatusIndicator(inspection.inspectionState)
        
        Spacer(modifier = Modifier.width(12.dp))
        
        Column(
            modifier = Modifier.weight(1f)
        ) {
            Text(
                text = inspection.workOrderId,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = "ID: ${inspection.productId}",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        
        Text(
            text = formatTimestamp(inspection.startedAt),
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun BottomActionBar(
    onSettingsClick: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.End
    ) {
        IconButton(onClick = onSettingsClick) {
            Icon(
                imageVector = Icons.Default.Settings,
                contentDescription = "設定"
            )
        }
    }
}

// Utility functions
private fun getStateDisplayText(state: InspectionState): String = when (state) {
    is InspectionState.ProductScanning -> "順序情報を選択してください"
    is InspectionState.ProductIdentified -> "順序情報が特定されました"
    is InspectionState.InProgress -> "検査実行中..."
    is InspectionState.AiCompleted -> "AI検査完了"
    is InspectionState.HumanReview -> "人による確認中"
    is InspectionState.Completed -> "検査完了"
    is InspectionState.ProductNotFound -> "順序情報が見つかりません"
    is InspectionState.QrDecodeFailed -> "QRコードの読み取りに失敗"
    is InspectionState.Failed -> "検査に失敗しました"
    is InspectionState.Cancelled -> "検査がキャンセルされました"
}

private fun formatTimestamp(timestamp: Long): String {
    // Simple timestamp formatting - in real app, use proper date formatting
    return java.text.SimpleDateFormat("MM/dd HH:mm", java.util.Locale.getDefault())
        .format(java.util.Date(timestamp))
}
