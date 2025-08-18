package com.imageflow.kmp.desktop

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Divider
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.ChipColors
import androidx.compose.ui.graphics.Color
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.foundation.Canvas
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.geometry.Offset
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.unit.Dp
import androidx.compose.foundation.clickable
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.imageflow.kmp.models.AiInspectionResult
import com.imageflow.kmp.models.ProductInfo
import com.imageflow.kmp.state.InspectionState
import androidx.compose.ui.graphics.toComposeImageBitmap

@Composable
fun DesktopInspectionDetailPanel(
    currentProduct: ProductInfo?,
    inspectionState: InspectionState,
    progress: Float,
    lastAiResult: AiInspectionResult?,
    isLoading: Boolean,
    errorMessage: String?,
    inspectionItems: List<com.imageflow.kmp.network.InspectionItemKmp> = emptyList(),
    okSnapshots: Map<String, Pair<ByteArray, List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>>> = emptyMap(),
    realtimeSnapshots: Map<String, Pair<Pair<ByteArray, List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>>, String?>> = emptyMap(),
    perItemHuman: Map<String, com.imageflow.kmp.models.HumanResult> = emptyMap(),
    currentIndex: Int = 0,
    onSelectItemIndex: (Int) -> Unit = {},
    onItemHumanReview: (String, com.imageflow.kmp.models.HumanResult) -> Unit = { _, _ -> },
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxWidth().padding(12.dp)) {
        // Top: Product target (left) + Status (right)
        Row(Modifier.fillMaxWidth()) {
            Column(Modifier.weight(3f).padding(end = 8.dp)) {
                Text("検査対象", style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(4.dp))
                if (currentProduct != null) {
                    Text("型式コード: ${currentProduct.productCode}", fontWeight = FontWeight.SemiBold)
                    Text("機番: ${currentProduct.machineNumber}")
                    Text("指図/指示: ${currentProduct.workOrderId} / ${currentProduct.instructionId}")
                    Text("生産日/連番: ${currentProduct.productionDate} / ${currentProduct.monthlySequence}")
                } else {
                    Text("型式未選択", color = MaterialTheme.colorScheme.error)
                }
            }
            Column(Modifier.weight(1f).padding(end = 8.dp)) {
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
            }
            // Realtime preview area (current item only)
            Column(Modifier.weight(2f)) {
                val ordered = inspectionItems.sortedBy { it.execution_order }
                val cur = if (currentIndex in ordered.indices) ordered[currentIndex] else null
                val rt = cur?.let { realtimeSnapshots[it.id] }
                Text("リアルタイム", style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(4.dp))
                if (rt != null) {
                    SnapshotWithOverlay(bytes = rt.first.first, detections = rt.first.second, compact = false)
                } else {
                    Text("待機中", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        HorizontalDivider()
        Spacer(Modifier.height(8.dp))
        // Items list (drum-roll: 全項目表示、現在項目を大きく、他は小さく)
        Column(modifier = Modifier.fillMaxWidth().verticalScroll(rememberScrollState())) {
            Text("検査項目 (${inspectionItems.size})", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(4.dp))
            val activePipelineId = lastAiResult?.pipelineId
            val ordered = inspectionItems.sortedBy { it.execution_order }
            ordered.forEachIndexed { idx, item ->
                val isCurrent = idx == currentIndex
                // Header row for item: name + AI status chip and 目視OK
                Row(Modifier.fillMaxWidth().padding(vertical = if (isCurrent) 4.dp else 2.dp).clickable { onSelectItemIndex(idx) }, horizontalArrangement = Arrangement.SpaceBetween) {
                    val nameStyle = if (isCurrent) MaterialTheme.typography.bodyMedium else MaterialTheme.typography.bodySmall
                    Text("[${item.execution_order}] ${item.name} (${item.type})", color = MaterialTheme.colorScheme.onSurfaceVariant, style = nameStyle)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        val aiStatus = if (okSnapshots.containsKey(item.id)) "OK" else realtimeSnapshots[item.id]?.second
                        if (aiStatus != null) {
                            val (al, ac) = when (aiStatus.uppercase()) {
                                "OK" -> "AI OK" to Color(0xFF2E7D32)
                                "NG" -> "AI NG" to Color(0xFFC62828)
                                else -> aiStatus.uppercase() to Color(0xFF616161)
                            }
                            AssistChip(onClick = {}, label = { Text(al, color = Color.White) }, colors = AssistChipDefaults.assistChipColors(containerColor = ac))
                        }
                        val humanOk = perItemHuman[item.id] == com.imageflow.kmp.models.HumanResult.OK
                        val humanColor = if (humanOk) Color(0xFF2E7D32) else Color(0xFF616161)
                        AssistChip(
                            onClick = { onItemHumanReview(item.id, com.imageflow.kmp.models.HumanResult.OK) },
                            label = { Text("目視OK", color = Color.White) },
                            colors = AssistChipDefaults.assistChipColors(containerColor = humanColor)
                        )
                    }
                }
                // Content row: last OK (left) | AI result (right)
                Row(Modifier.fillMaxWidth().padding(bottom = if (isCurrent) 8.dp else 4.dp)) {
                    // Last OK (left)
                    Column(Modifier.weight(1f).padding(end = 4.dp)) {
                        val ok = okSnapshots[item.id]
                        if (ok != null) SnapshotWithOverlay(bytes = ok.first, detections = ok.second, compact = !isCurrent)
                        else Text(if (isCurrent) "OK画像なし" else "", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    // AI result (right)
                    Column(Modifier.weight(1f).padding(start = 4.dp)) {
                        if (isCurrent && !activePipelineId.isNullOrBlank() && item.pipeline_id == activePipelineId && lastAiResult != null) {
                            Text("判定: ${lastAiResult.overallResult}")
                            Text("信頼度: ${(lastAiResult.confidence * 100).toInt()}%")
                            Text("処理時間: ${lastAiResult.processingTimeMs}ms")
                            Text("検出: ${lastAiResult.detectedDefects.size}件", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        } else if (isCurrent) {
                            Text("AI結果なし", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
                HorizontalDivider()
            }
        }
    }
}

private fun stateLabel(state: InspectionState): String = when (state) {
    InspectionState.ProductScanning -> "スキャン待ち"
    InspectionState.ProductIdentified -> "型式特定済み"
    InspectionState.InProgress -> "検査実行中"
    InspectionState.AiCompleted -> "AI判定完了"
    InspectionState.HumanReview -> "人手確認中"
    InspectionState.Completed -> "完了"
    InspectionState.ProductNotFound -> "型式未検出"
    InspectionState.QrDecodeFailed -> "QR失敗"
    InspectionState.Failed -> "失敗"
    InspectionState.Cancelled -> "キャンセル"
}

@Composable
private fun SnapshotWithOverlay(
    bytes: ByteArray,
    detections: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>,
    compact: Boolean = false
) {
    val img = remember(bytes) {
        kotlin.runCatching { org.jetbrains.skia.Image.makeFromEncoded(bytes).toComposeImageBitmap() }.getOrNull()
    }
    if (img == null) return
    val density = LocalDensity.current
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        val imgW = img.width
        val imgH = img.height
        val boxW = maxWidth
        val scale = with(density) { boxW.toPx() / imgW.toFloat() }
        val boxHdp = with(density) { (imgH.toFloat() * scale).toDp() }
        val h = if (compact) boxHdp * 0.6f else boxHdp
        Box(Modifier.width(boxW).height(h)) {
            Image(bitmap = img, contentDescription = "OK snapshot", modifier = Modifier.matchParentSize())
            Canvas(Modifier.matchParentSize()) {
                val sx = size.width / imgW.toFloat()
                val sy = size.height / imgH.toFloat()
                detections.forEach { d ->
                    val x = d.x1 * sx
                    val y = d.y1 * sy
                    val w = (d.x2 - d.x1) * sx
                    val h = (d.y2 - d.y1) * sy
                    drawRect(
                        color = Color(0xFF00C8FF),
                        topLeft = Offset(x, y),
                        size = Size(w, h),
                        style = Stroke(width = 2f)
                    )
                }
            }
            // Simple labels placed above top-left of each box
            detections.forEach { d ->
                val sx = with(density) { (boxW.toPx() / imgW.toFloat()) }
                val sy = sx
                val xdp = with(density) { (d.x1 * sx).toDp() }
                val ydp = with(density) { (d.y1 * sy).toDp() }
                Box(Modifier.offset(xdp, ydp).padding(2.dp)) {
                    AssistChip(onClick = {}, label = { Text("${d.className} ${"%.0f".format(d.confidence * 100)}%") })
                }
            }
        }
    }
}
