package com.imageflow.kmp.desktop

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.runtime.snapshotFlow
import kotlinx.coroutines.flow.collectLatest
import androidx.compose.material3.Divider
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.ChipColors
import androidx.compose.ui.graphics.Color
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import kotlinx.coroutines.delay
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
import androidx.compose.foundation.background
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.unit.Dp
import androidx.compose.foundation.clickable
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.layout.boundsInParent
import com.imageflow.kmp.models.AiInspectionResult
import com.imageflow.kmp.models.ProductInfo
import com.imageflow.kmp.state.InspectionState
import androidx.compose.ui.graphics.toComposeImageBitmap

@Composable
fun DesktopInspectionDetailPanel(
    currentProduct: ProductInfo?,
    processCode: String? = null,
    processName: String? = null,
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
    // Optional: request programmatic scroll to a specific index (e.g., after human OK)
    scrollRequestIndex: Int? = null,
    scrollRequestSeq: Int = 0,
    onSelectItemIndex: (Int) -> Unit = {},
    onItemHumanReview: (String, com.imageflow.kmp.models.HumanResult) -> Unit = { _, _ -> },
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxSize().padding(12.dp)) {
        // Top: Product target (left) + Status (right)
        Row(Modifier.fillMaxWidth()) {
            Column(Modifier.weight(3f).padding(end = 8.dp)) {
                // 工程コードはトップバー右側に表示。ここでは工程名のみ任意表示。
                if (!processName.isNullOrBlank()) {
                    Spacer(Modifier.height(2.dp))
                    Text("工程名: ${processName}")
                }
                Spacer(Modifier.height(6.dp))
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
            // Realtime preview area (current item only)
            Column(Modifier.weight(2f)) {
                val ordered = inspectionItems.sortedBy { it.execution_order }
                val cur = if (currentIndex in ordered.indices) ordered[currentIndex] else null
                val curId = cur?.id
                val humanOk = curId?.let { perItemHuman[it] == com.imageflow.kmp.models.HumanResult.OK } == true
                val okSnap = curId?.let { okSnapshots[it] }
                val rt = curId?.let { realtimeSnapshots[it] }
                Text("リアルタイム", style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(4.dp))
                val maxH = 200.dp
                when {
                    // After human OK, show the sticky OK snapshot here; do not open stream
                    humanOk && okSnap != null -> SnapshotWithOverlay(bytes = okSnap.first, detections = okSnap.second, compact = false, showOverlay = false, maxHeightDp = maxH)
                    // Otherwise, show live preview for current item without overlays
                    rt != null -> SnapshotWithOverlay(bytes = rt.first.first, detections = rt.first.second, compact = false, showOverlay = false, maxHeightDp = maxH)
                    else -> Box(Modifier.fillMaxWidth().height(maxH)) { Text("待機中", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                }
            }
        }
        HorizontalDivider()
        Spacer(Modifier.height(8.dp))
        // Items list as LazyColumn for reliable top-aligned auto-scroll
        val listState = rememberLazyListState()
        val ordered = inspectionItems.sortedBy { it.execution_order }
        Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
            LazyColumn(state = listState, modifier = Modifier.fillMaxSize()) {
                item(key = "header") {
                    Text("検査項目 (${inspectionItems.size})", style = MaterialTheme.typography.titleSmall)
                    Spacer(Modifier.height(4.dp))
                }
                itemsIndexed(ordered, key = { _, it -> it.id }) { idx, item ->
                    // Header row for item: name + AI status chip and 目視OK
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                            .clickable { onSelectItemIndex(idx) },
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        val nameStyle = MaterialTheme.typography.bodySmall
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
                    // Content row
                    Row(Modifier.fillMaxWidth().padding(bottom = 6.dp)) {
                        Column(Modifier.fillMaxWidth()) {
                            val ok = okSnapshots[item.id]
                            val rt = realtimeSnapshots[item.id]
                            val maxH = 240.dp
                            when {
                                ok != null -> SnapshotWithOverlay(bytes = ok.first, detections = ok.second, compact = false, showOverlay = true, maxHeightDp = maxH)
                                rt != null -> SnapshotWithOverlay(bytes = rt.first.first, detections = rt.first.second, compact = false, showOverlay = true, maxHeightDp = maxH)
                                else -> Text("OK画像なし", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                    HorizontalDivider()
                }
            }
        }
        // Note: We no longer auto-select based on scroll position to avoid
        // fighting with programmatic selection after human OK.
        // Programmatic scroll to requested item index (align to top)
        LaunchedEffect(scrollRequestSeq) {
            val idx = scrollRequestIndex ?: return@LaunchedEffect
            // Wait a tick for the list to compose items (robust on Desktop)
            kotlinx.coroutines.yield()
            // Ensure the target index exists before animating
            var tries = 0
            while (tries < 30) {
                val total = listState.layoutInfo.totalItemsCount
                if (total >= 1 + (ordered.size)) break
                tries++
                delay(16)
            }
            val target = 1 + idx
            // Force position instantly first, then animate to absorb any small layout diff
            runCatching { listState.scrollToItem(index = target, scrollOffset = 0) }
            listState.animateScrollToItem(index = target, scrollOffset = 0)
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
    compact: Boolean = false,
    showOverlay: Boolean = true,
    maxHeightDp: Dp? = null
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
        var h = if (compact) boxHdp * 0.6f else boxHdp
        maxHeightDp?.let { limit -> if (h > limit) h = limit }
        Box(Modifier.width(boxW).height(h)) {
            Image(bitmap = img, contentDescription = "OK snapshot", modifier = Modifier.matchParentSize())
            if (showOverlay) {
                // Compute actual draw area (letterboxing aware): scale = min, with offsets
                Canvas(Modifier.matchParentSize()) {
                    val scale = kotlin.math.min(size.width / imgW.toFloat(), size.height / imgH.toFloat())
                    val drawW = imgW * scale
                    val drawH = imgH * scale
                    val offX = (size.width - drawW) / 2f
                    val offY = (size.height - drawH) / 2f
                    detections.forEach { d ->
                        val x = offX + d.x1 * scale
                        val y = offY + d.y1 * scale
                        val w = (d.x2 - d.x1) * scale
                        val h = (d.y2 - d.y1) * scale
                        drawRect(
                            color = Color(0xFFC62828), // red for better contrast
                            topLeft = Offset(x, y),
                            size = Size(w, h),
                            style = Stroke(width = 2f)
                        )
                    }
                }
                // Place labels using same offsets/scale as above
                val scale = kotlin.math.min(with(density) { (boxW.toPx()) } / imgW.toFloat(), with(density) { (h.toPx()) } / imgH.toFloat())
                val drawW = imgW * scale
                val drawH = imgH * scale
                val offX = (with(density) { boxW.toPx() } - drawW) / 2f
                val offY = (with(density) { h.toPx() } - drawH) / 2f
                detections.forEach { d ->
                    val xdp = with(density) { (offX + d.x1 * scale).toDp() }
                    val ydp = with(density) { (offY + d.y1 * scale).toDp() }
                    Box(
                        Modifier
                            .offset(xdp, ydp)
                            .padding(2.dp)
                            .border(1.dp, Color(0xFFFFCDD2))
                            .background(Color(0x44000000))  // higher transparency
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "${d.className} ${"%.0f".format(d.confidence * 100)}%",
                            color = Color.White,
                            style = MaterialTheme.typography.labelSmall
                        )
                    }
                }
            }
        }
    }
}
