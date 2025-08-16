package com.imageflow.kmp.ui.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.imageflow.kmp.models.AiInspectionResult
import com.imageflow.kmp.models.HumanResult
import com.imageflow.kmp.models.ProductInfo
import com.imageflow.kmp.state.InspectionState

@Composable
fun InspectionDetailScreen(
    currentProduct: ProductInfo?,
    inspectionState: InspectionState,
    progress: Float,
    lastAiResult: AiInspectionResult?,
    isLoading: Boolean,
    errorMessage: String?,
    onAddImage: (String) -> Unit,
    onRunAi: () -> Unit,
    onHumanReview: (HumanResult) -> Unit,
    onBack: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Card {
            Column(Modifier.fillMaxWidth().padding(12.dp)) {
                Text("検査詳細", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(4.dp))
                if (currentProduct != null) {
                    Text("製品: ${currentProduct.productType} - ${currentProduct.machineNumber}", fontWeight = FontWeight.SemiBold)
                    Text("指図: ${currentProduct.workOrderId} / 指示: ${currentProduct.instructionId}")
                    Text("生産日: ${currentProduct.productionDate} / 連番: ${currentProduct.monthlySequence}")
                } else {
                    Text("製品が選択されていません", color = MaterialTheme.colorScheme.error)
                }
            }
        }

        if (inspectionState != InspectionState.ProductScanning) {
            Card {
                Column(Modifier.fillMaxWidth().padding(12.dp)) {
                    Text("進行状況")
                    Spacer(Modifier.height(8.dp))
                    LinearProgressIndicator(progress = progress, modifier = Modifier.fillMaxWidth())
                    Spacer(Modifier.height(4.dp))
                    Text("${(progress * 100).toInt()}% / 状態: ${stateLabel(inspectionState)}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        Card {
            Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("操作")
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        val path = "image_${kotlin.random.Random.nextInt(0, 1_000_000)}.jpg"
                        onAddImage(path)
                    }, enabled = currentProduct != null) { Text("画像を追加") }
                    OutlinedButton(onClick = onRunAi, enabled = currentProduct != null) { Text("AI判定") }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { onHumanReview(HumanResult.OK) }, enabled = currentProduct != null) { Text("人手確認: OK") }
                    OutlinedButton(onClick = { onHumanReview(HumanResult.NG) }, enabled = currentProduct != null) { Text("人手確認: NG") }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onBack) { Text("戻る") }
                }
            }
        }

        Card {
            Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("結果")
                if (isLoading) {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                    Text("処理中...", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                errorMessage?.let { Text("エラー: $it", color = MaterialTheme.colorScheme.error) }
                if (lastAiResult != null) {
                    Text("AI判定: ${lastAiResult.overallResult}")
                    Text("信頼度: ${(lastAiResult.confidence * 100).toInt()}% / 処理: ${lastAiResult.processingTimeMs}ms")
                    if (lastAiResult.detectedDefects.isNotEmpty()) {
                        Text("検出不良: ${lastAiResult.detectedDefects.size}件", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                } else {
                    Text("AI結果はありません", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        Spacer(Modifier.weight(1f))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onBack) { Text("戻る") }
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
