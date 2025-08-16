package com.imageflow.kmp.desktop

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.imageflow.kmp.models.AiInspectionResult
import com.imageflow.kmp.models.ProductInfo
import com.imageflow.kmp.state.InspectionState

@Composable
fun DesktopInspectionDetailPanel(
    currentProduct: ProductInfo?,
    inspectionState: InspectionState,
    progress: Float,
    lastAiResult: AiInspectionResult?,
    isLoading: Boolean,
    errorMessage: String?,
    inspectionItems: List<com.imageflow.kmp.network.InspectionItemKmp> = emptyList(),
    modifier: Modifier = Modifier
) {
    Row(modifier = modifier.fillMaxWidth().padding(12.dp)) {
        // Left: Product + Items
        Column(modifier = Modifier.weight(1f).padding(end = 12.dp).verticalScroll(rememberScrollState())) {
            // Product summary (compact)
            Text("検査対象", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(4.dp))
            if (currentProduct != null) {
                Text("製品: ${currentProduct.productCode}", fontWeight = FontWeight.SemiBold)
                Text("機番: ${currentProduct.machineNumber}")
                Text("指図/指示: ${currentProduct.workOrderId} / ${currentProduct.instructionId}")
                Text("生産日/連番: ${currentProduct.productionDate} / ${currentProduct.monthlySequence}")
            } else {
                Text("製品未選択", color = MaterialTheme.colorScheme.error)
            }
            Spacer(Modifier.height(12.dp))
            Divider()
            Spacer(Modifier.height(8.dp))
            // Items (compact list)
            Text("検査項目 (${inspectionItems.size})", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(4.dp))
            inspectionItems.sortedBy { it.execution_order }.forEach { item ->
                Text("[${item.execution_order}] ${item.name} (${item.type})", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }

        // Right: Results
        Column(modifier = Modifier.width(360.dp)) {
            Text("状態", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(4.dp))
            val pct = (progress * 100).toInt()
            Text("${stateLabel(inspectionState)} / ${pct}%")
            if (isLoading) {
                Spacer(Modifier.height(4.dp))
                Text("処理中...", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            errorMessage?.let {
                Spacer(Modifier.height(4.dp))
                Text("エラー: ${it}", color = MaterialTheme.colorScheme.error)
            }
            Spacer(Modifier.height(8.dp))
            Divider()
            Spacer(Modifier.height(8.dp))
            Text("AI結果", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(4.dp))
            if (lastAiResult != null) {
                Text("判定: ${lastAiResult.overallResult}")
                Text("信頼度: ${(lastAiResult.confidence * 100).toInt()}%")
                Text("処理時間: ${lastAiResult.processingTimeMs}ms")
                val cnt = lastAiResult.detectedDefects.size
                Text("検出不良: ${cnt}件", color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                Text("AI結果はありません", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

private fun stateLabel(state: InspectionState): String = when (state) {
    InspectionState.ProductScanning -> "スキャン待ち"
    InspectionState.ProductIdentified -> "製品特定済み"
    InspectionState.InProgress -> "検査実行中"
    InspectionState.AiCompleted -> "AI判定完了"
    InspectionState.HumanReview -> "人手確認中"
    InspectionState.Completed -> "完了"
    InspectionState.ProductNotFound -> "製品未検出"
    InspectionState.QrDecodeFailed -> "QR失敗"
    InspectionState.Failed -> "失敗"
    InspectionState.Cancelled -> "キャンセル"
}

