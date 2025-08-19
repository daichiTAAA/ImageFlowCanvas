package com.imageflow.kmp.desktop

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.awt.SwingPanel
import java.awt.Desktop
import java.net.URI
import io.grpc.ManagedChannel
import io.grpc.ManagedChannelBuilder
import imageflow.v1.CameraStreamProcessorGrpcKt
import imageflow.v1.CameraStream
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest
import java.awt.BorderLayout
import java.awt.image.BufferedImage
import java.io.ByteArrayOutputStream
import javax.imageio.ImageIO
import javax.swing.JPanel
import org.bytedeco.javacv.FFmpegFrameGrabber
import org.bytedeco.javacv.FFmpegFrameFilter
import org.bytedeco.javacv.Java2DFrameConverter
import org.bytedeco.javacv.Frame
import org.bytedeco.ffmpeg.global.avutil.AV_PIX_FMT_BGR0
import org.slf4j.LoggerFactory
import javax.swing.SwingUtilities
private val LOG = LoggerFactory.getLogger("RealtimeInspection")

@Composable
fun RealtimeInspectionDesktop(
    grpcHost: String,
    grpcPort: Int,
    pipelineId: String?,
    authToken: String? = null,
    processingParams: Map<String, String> = emptyMap(),
    modifier: Modifier = Modifier,
    orderLabel: String? = null,
    renderUi: Boolean = true,
    targetItemId: String? = null,
    onDetectionsUpdated: ((detections: Int, processingTimeMs: Long) -> Unit)? = null,
    onRealtimeUpdate: ((detections: Int, processingTimeMs: Long, pipelineId: String?, details: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>, serverJudgment: String?) -> Unit)? = null,
    onOkSnapshot: ((pipelineId: String?, jpegBytes: ByteArray, details: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>) -> Unit)? = null,
    onPreviewFrame: ((pipelineId: String?, jpegBytes: ByteArray, details: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>, serverJudgment: String?) -> Unit)? = null
) {
    val log = remember { LOG }
    var grabber by remember { mutableStateOf<FFmpegFrameGrabber?>(null) }
    var imagePanel by remember { mutableStateOf<RtPreviewPanel?>(null) }
    // no explicit RGB filter; enforce pixel_format at grabber level
    var lastServerJudgment by remember { mutableStateOf<String?>(null) }
    var channel by remember { mutableStateOf<ManagedChannel?>(null) }
    // Keep latest processing params updated even if stream stays alive
    val procParamsRef = remember { java.util.concurrent.atomic.AtomicReference<Map<String, String>>(processingParams) }
    LaunchedEffect(processingParams) { procParamsRef.set(processingParams) }
    var running by remember { mutableStateOf(true) } // 自動開始
    var stats by remember { mutableStateOf(Stats()) }
    var frameCount by remember { mutableStateOf(0) }
    var startAt by remember { mutableStateOf(0L) }
    var configVersion by remember { mutableStateOf(0) }
    // Simple camera controls
    var deviceIndex by remember { mutableStateOf(0) }
    var pixelFmt by remember { mutableStateOf(PixelFmt.RGB0) }
    var resolution by remember { mutableStateOf(Res(1280, 720)) }
    var fps by remember { mutableStateOf(30) }

    DisposableEffect(Unit) {
        onDispose {
            try { grabber?.stop() } catch (_: Throwable) {}
            try { grabber?.release() } catch (_: Throwable) {}
            try { channel?.shutdownNow() } catch (_: Throwable) {}
        }
    }

    Column(modifier = modifier.fillMaxWidth().background(Color.Black)) {
        if (renderUi) Row(Modifier.fillMaxWidth().padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("gRPC ${grpcHost}:${grpcPort}", color = Color.White)
            Spacer(Modifier.width(16.dp))
            Text("Frames: ${stats.frames} / Detections: ${stats.lastDetections}", color = Color.LightGray)
            Spacer(Modifier.weight(1f))
            if (!orderLabel.isNullOrBlank()) {
                AssistChip(label = { Text(orderLabel) }, onClick = { })
                Spacer(Modifier.width(8.dp))
            }
            // Minimal camera control chips
            AssistChip(label = { Text("Dev ${deviceIndex}") }, onClick = { deviceIndex = if (deviceIndex == 0) 1 else 0 })
            Spacer(Modifier.width(8.dp))
            AssistChip(label = { Text(pixelFmt.label) }, onClick = { pixelFmt = if (pixelFmt == PixelFmt.BGR0) PixelFmt.RGB0 else PixelFmt.BGR0 })
            Spacer(Modifier.width(8.dp))
            AssistChip(label = { Text("${resolution.w}x${resolution.h}") }, onClick = {
                resolution = if (resolution.w == 1280) Res(640, 480) else Res(1280, 720)
            })
            Spacer(Modifier.width(8.dp))
            AssistChip(label = { Text("${fps}fps") }, onClick = { fps = if (fps == 30) 10 else 30 })
            Spacer(Modifier.width(8.dp))
            OutlinedButton(onClick = {
                // trigger clean restart via state key; LaunchedEffect will cancel and re-init safely
                frameCount = 0
                startAt = 0L
                configVersion++
            }) { Text("適用") }
            Spacer(Modifier.width(8.dp))
            OutlinedButton(onClick = { running = !running }) { Text(if (running) "停止" else "開始") }
        }

        if (renderUi) Box(Modifier.fillMaxWidth().height(360.dp).background(Color.Black)) {
            if (imagePanel == null) imagePanel = RtPreviewPanel()
            SwingPanelHost(imagePanel)
        }
    }

    // Always call latest callbacks even if this LaunchedEffect doesn't restart
    val onDetectionsUpdatedState = rememberUpdatedState(onDetectionsUpdated)
    val onRealtimeUpdateState = rememberUpdatedState(onRealtimeUpdate)
    val onOkSnapshotState = rememberUpdatedState(onOkSnapshot)
    val onPreviewFrameState = rememberUpdatedState(onPreviewFrame)

    LaunchedEffect(running, deviceIndex, resolution, fps, pixelFmt, configVersion, pipelineId) {
        if (!running) return@LaunchedEffect
        // 重い処理はIOに退避（UIブロック回避）
        withContext(Dispatchers.IO) {
            // Cooldown to allow previous camera/stream to release when pipeline changes
            try { delay(500) } catch (_: Throwable) {}
            channel = ManagedChannelBuilder.forAddress(grpcHost, grpcPort)
                .usePlaintext()
                .build()
            var stub = CameraStreamProcessorGrpcKt.CameraStreamProcessorCoroutineStub(channel!!)
            if (!authToken.isNullOrBlank()) {
                val md = io.grpc.Metadata().apply {
                    val key = io.grpc.Metadata.Key.of("authorization", io.grpc.Metadata.ASCII_STRING_MARSHALLER)
                    this.put(key, "Bearer $authToken")
                }
                val interceptor = io.grpc.stub.MetadataUtils.newAttachHeadersInterceptor(md)
                stub = stub.withInterceptors(interceptor)
            }

            // Print device list to logs (helps on macOS to pick the right index)
            try { listAvFoundationDevices() } catch (_: Throwable) {}

            // Retry camera init a few times to handle rapid re-initialization between pipelines
            var g: FFmpegFrameGrabber? = null
            var tries = 0
            while (tries < 3 && g == null) {
                tries++
                try {
                    // Try requested pixel format first
                    g = initGrabber(deviceIndex, resolution, fps, pixelFmt)
                        ?: FFmpegFrameGrabber(deviceIndex.toString()).apply {
                            format = "avfoundation"
                            imageWidth = resolution.w
                            imageHeight = resolution.h
                            audioChannels = 0
                            setOption("video_device_index", deviceIndex.toString())
                            setOption("pixel_format", pixelFmt.ffmpegOpt)
                            start()
                        }
                    // If still null, try the opposite pixel format as a fallback
                    if (g == null) {
                        val altFmt = if (pixelFmt == PixelFmt.RGB0) PixelFmt.BGR0 else PixelFmt.RGB0
                        g = initGrabber(deviceIndex, resolution, fps, altFmt)
                    }
                } catch (t: Throwable) {
                    log.warn("Camera init retry {} failed: {}", tries, t.message)
                    try { g?.stop() } catch (_: Throwable) {}
                    try { g?.release() } catch (_: Throwable) {}
                    g = null
                    try { delay(150) } catch (_: Throwable) {}
                }
            }
            if (g == null) throw IllegalStateException("Failed to initialize camera after retries")
            grabber = g
            val converter = Java2DFrameConverter()
            // Warm-up: drop initial frames to stabilize timebase
            try {
                repeat(10) { _ -> g?.grab() }
            } catch (_: Throwable) {}

            val requests = kotlinx.coroutines.flow.MutableSharedFlow<CameraStream.VideoFrame>(extraBufferCapacity = 2)
            var latestJpeg: ByteArray? = null
            val recvJob = launch(Dispatchers.IO) {
                try {
                    stub.processVideoStream(requests).collect { resp ->
                        withContext(Dispatchers.Main) {
                            stats = stats.copy(lastDetections = resp.detectionsCount)
                            // Map detections to shared VM DTOs
                            val details = resp.detectionsList.map { d ->
                                com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection(
                                    className = d.className,
                                    confidence = d.confidence,
                                    x1 = d.bbox.x1,
                                    y1 = d.bbox.y1,
                                    x2 = d.bbox.x2,
                                    y2 = d.bbox.y2
                                )
                            }
                            // Prefer server-side fields if available
                            val serverPipelineId = if (resp.pipelineId.isNullOrBlank()) pipelineId else resp.pipelineId
                            onDetectionsUpdatedState.value?.invoke(resp.detectionsCount, resp.processingTimeMs)
                            val serverJudgment = try { resp.judgment } catch (_: Throwable) { null }
                            lastServerJudgment = serverJudgment
                            // Update overlay on preview
                            if (renderUi) imagePanel?.setOverlay(details, serverJudgment)
                            onRealtimeUpdateState.value?.invoke(
                                resp.detectionsCount,
                                resp.processingTimeMs,
                                serverPipelineId,
                                details,
                                serverJudgment
                            )
                            // If server judgment is OK, emit snapshot bytes for persistence
                            if ((serverPipelineId?.isNotBlank() == true || !targetItemId.isNullOrBlank()) && (serverJudgment?.equals("OK", ignoreCase = true) == true)) {
                                latestJpeg?.let { jpg ->
                                    try { onOkSnapshotState.value?.invoke(serverPipelineId, jpg, details) } catch (_: Throwable) { }
                                }
                            }
                            latestJpeg?.let { jpg ->
                                try { onPreviewFrameState.value?.invoke(serverPipelineId, jpg, details, serverJudgment) } catch (_: Throwable) { }
                            }
                            // Note: ViewModel signature updated to accept server judgment; Main.kt will forward it
                        }
                    }
                } catch (t: Throwable) {
                    log.error("[Desktop] gRPC receive stream error: ${t.message}", t)
                }
            }

            try {
                withContext(Dispatchers.Main) { startAt = System.currentTimeMillis(); frameCount = 0 }
                while (isActive && running) {
                    val raw: Frame? = try { g?.grab() } catch (t: Throwable) {
                        log.warn("grab failed: {}", t.message)
                        null
                    }
                    val frame: Frame? = raw
                    val img0 = frame?.let { converter.convert(it) }
                    val img = img0?.let { ensureRgb(it) } ?: continue
                    SwingUtilities.invokeLater { imagePanel?.setImage(img) }
                    withContext(Dispatchers.Main) { frameCount += 1 }
                    val bytes = encodeJpeg(img)
                    latestJpeg = bytes
                    // Emit a preview frame even before server returns any detections
                    try {
                        onPreviewFrameState.value?.invoke(pipelineId, bytes, emptyList(), lastServerJudgment)
                    } catch (_: Throwable) { }
                    val metaBuilder = CameraStream.VideoMetadata.newBuilder()
                        .setSourceId("desktop-usb-0")
                        .setWidth(img.width)
                        .setHeight(img.height)
                    if (!pipelineId.isNullOrBlank()) {
                        metaBuilder.setPipelineId(pipelineId)
                    }
                    val pp = procParamsRef.get()
                    if (pp.isNotEmpty()) metaBuilder.putAllProcessingParams(pp)
                    val meta = metaBuilder.build()
                    val vf = CameraStream.VideoFrame.newBuilder()
                        .setFrameData(com.google.protobuf.ByteString.copyFrom(bytes))
                        .setTimestampMs(System.currentTimeMillis())
                        .setMetadata(meta)
                        .build()
                    val ok = requests.tryEmit(vf)
                    if (!ok) {
                        log.warn("[Desktop] Dropped frame due to backpressure")
                    }
                    withContext(Dispatchers.Main) { stats = stats.copy(frames = stats.frames + 1) }
                    // Preview/send at ~4 FPS to keep load modest
                    delay(250)
                }
            } finally {
                log.info("[Desktop] Closing gRPC stream and camera")
                recvJob.cancel()
                try { g?.stop() } catch (_: Throwable) {}
                try { g?.release() } catch (_: Throwable) {}
                try { channel?.shutdownNow() } catch (_: Throwable) {}
            }
        }
    }
}

private fun encodeJpeg(img: BufferedImage): ByteArray {
    val baos = ByteArrayOutputStream()
    ImageIO.write(img, "jpg", baos)
    return baos.toByteArray()
}

@Composable
private fun SwingPanelHost(panel: JPanel?) {
    androidx.compose.ui.awt.SwingPanel(
        modifier = Modifier.fillMaxSize(),
        factory = {
            JPanel(BorderLayout()).apply {
                background = java.awt.Color.BLACK
                if (panel != null) add(panel, BorderLayout.CENTER)
            }
        },
        update = { container ->
            val root = container as JPanel
            root.removeAll()
            root.add(panel ?: JPanel().apply { background = java.awt.Color.BLACK }, BorderLayout.CENTER)
            root.revalidate()
            root.repaint()
        }
    )
}

private class RtPreviewPanel : JPanel() {
    @Volatile private var image: BufferedImage? = null
    @Volatile private var overlay: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection> = emptyList()
    @Volatile private var serverJudgment: String? = null

    fun setImage(img: BufferedImage) { image = img; repaint() }
    fun setOverlay(
        detections: List<com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel.RealtimeDetection>,
        judgment: String?
    ) { overlay = detections; serverJudgment = judgment; repaint() }

    override fun paintComponent(g: java.awt.Graphics) {
        super.paintComponent(g)
        val img = image ?: return
        val g2 = g as java.awt.Graphics2D
        g2.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_ON)

        val panelW = width.toDouble()
        val panelH = height.toDouble()
        val imgW = img.width.toDouble()
        val imgH = img.height.toDouble()
        val scale = kotlin.math.min(panelW / imgW, panelH / imgH)
        val drawW = (imgW * scale).toInt()
        val drawH = (imgH * scale).toInt()
        val offX = (panelW - drawW) / 2.0
        val offY = (panelH - drawH) / 2.0

        // draw image
        g2.drawImage(img, offX.toInt(), offY.toInt(), drawW, drawH, null)

        // overlay: bounding boxes
        val strokeW = (2.0 * kotlin.math.max(1.0, scale)).toFloat()
        g2.stroke = java.awt.BasicStroke(strokeW)

        fun drawLabel(x: Int, y: Int, text: String, bg: java.awt.Color) {
            val fm = g2.fontMetrics
            val pad = 4
            val tw = fm.stringWidth(text) + pad * 2
            val th = fm.height + pad
            g2.color = java.awt.Color(bg.red, bg.green, bg.blue, 180)
            g2.fillRect(x, (y - th).coerceAtLeast(0), tw, th)
            g2.color = java.awt.Color.WHITE
            g2.drawString(text, x + pad, (y - pad).coerceAtLeast(fm.ascent))
        }

        // draw detections
        for (d in overlay) {
            val x1 = (offX + d.x1 * scale).toInt()
            val y1 = (offY + d.y1 * scale).toInt()
            val w = ((d.x2 - d.x1) * scale).toInt()
            val h = ((d.y2 - d.y1) * scale).toInt()
            val color = java.awt.Color(200, 0, 0) // red for visibility
            g2.color = color
            g2.drawRect(x1, y1, w, h)
            val label = buildString {
                append(d.className)
                append(" ")
                append(String.format("%.0f%%", d.confidence * 100f))
            }
            drawLabel(x1, y1, label, color)
        }

        // server judgment badge
        serverJudgment?.let { j ->
            val jUpper = j.uppercase()
            val (txt, bg) = when (jUpper) {
                "OK" -> "OK" to java.awt.Color(0, 160, 0)
                "NG" -> "NG" to java.awt.Color(200, 0, 0)
                "PENDING" -> "PENDING" to java.awt.Color(200, 140, 0)
                else -> jUpper to java.awt.Color(80, 80, 80)
            }
            g2.font = g2.font.deriveFont(14f)
            drawLabel(offX.toInt() + 8, (offY + 24).toInt(), txt, bg)
        }
    }
}

private data class Stats(
    val frames: Int = 0,
    val lastDetections: Int = 0
)

private fun openBestAvFoundationGrabber(): FFmpegFrameGrabber? {
    val candidates = listOf("0", "1", "0:0", "1:0")
    for (dev in candidates) {
        try {
            val g = FFmpegFrameGrabber(dev)
            g.format = "avfoundation"
            g.frameRate = 30.0
            g.imageWidth = 1280
            g.imageHeight = 720
            g.pixelFormat = AV_PIX_FMT_BGR0
            g.audioChannels = 0
            g.start()
            val frame = g.grab()
            if (frame != null) return g
            g.stop(); g.release()
        } catch (_: Throwable) {
            // try next device string
        }
    }
    return null
}

// Make RGB normalization available to this file
private fun ensureRgb(src: BufferedImage): BufferedImage {
    if (src.type == BufferedImage.TYPE_INT_RGB) return src
    val converted = BufferedImage(src.width, src.height, BufferedImage.TYPE_INT_RGB)
    val g = converted.createGraphics()
    try {
        g.drawImage(src, 0, 0, null)
    } finally {
        g.dispose()
    }
    return converted
}

private enum class PixelFmt(val label: String, val ffmpegOpt: String) { RGB0("0rgb", "0rgb"), BGR0("bgr0", "bgr0");
    fun flip() = if (this == RGB0) BGR0 else RGB0
}

private data class Res(val w: Int, val h: Int)

private fun initGrabber(deviceIndex: Int, res: Res, fps: Int?, fmt: PixelFmt): FFmpegFrameGrabber? {
    return try {
        val g = FFmpegFrameGrabber(deviceIndex.toString())
        g.format = "avfoundation"
        g.imageWidth = res.w
        g.imageHeight = res.h
        g.audioChannels = 0
        // Enforce pixel format to avoid red/blue channel swap on macOS
        g.setOption("pixel_format", fmt.ffmpegOpt)
        g.setOption("video_size", "${res.w}x${res.h}")
        if (fps != null) {
            val fpsStr = String.format(java.util.Locale.US, "%.6f", if (fps == 30) 30.000030 else fps.toDouble())
            g.setOption("framerate", fpsStr)
            g.frameRate = if (fps == 30) 30.000030 else fps.toDouble()
        }
        g.setOption("video_device_index", deviceIndex.toString())
        g.setOption("audio_device_index", "-1")
        // Help avfoundation deliver frames sooner
        g.setOption("probesize", "20000000")
        g.setOption("analyzeduration", "20000000")
        g.setOption("use_wallclock_as_timestamps", "1")
        LOG.info("Init grabber dev={} size={}x{} fps={} fmt={} ...", deviceIndex, res.w, res.h, fps ?: -1, fmt.label)
        g.start()
        // Do not pre-grab; let the main loop warm up and display as soon as frames arrive
        g
    } catch (t: Throwable) {
        LOG.warn("Init failed dev={} size={}x{} fps={} fmt={}: {}", deviceIndex, res.w, res.h, fps ?: -1, fmt.label, t.message)
        null
    }
}

// Trigger avfoundation to list devices to the log (JavaCPP/SLF4J)
private fun listAvFoundationDevices() {
    try {
        val lister = FFmpegFrameGrabber("")
        lister.format = "avfoundation"
        lister.setOption("list_devices", "true")
        try { lister.start() } catch (_: Throwable) {}
        try { lister.stop() } catch (_: Throwable) {}
        try { lister.release() } catch (_: Throwable) {}
    } catch (_: Throwable) {
        // ignore
    }
}

@Composable
private fun PermissionHelpOverlay(
    onOpenSettings: () -> Unit,
    onRetryInit: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xCC000000)),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("カメラ映像を表示できません", color = Color.White)
            Spacer(Modifier.height(8.dp))
            Text(
                "カメラ権限が未許可の可能性があります。システム設定→プライバシーとセキュリティ→カメラで ImageFlowDesktop を許可してください。",
                color = Color.LightGray
            )
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onOpenSettings) { Text("カメラ設定を開く") }
                OutlinedButton(onClick = onRetryInit) { Text("再初期化") }
            }
        }
    }
}

private fun openPrivacyCameraSettings() {
    val uri = try { URI("x-apple.systempreferences:com.apple.preference.security?Privacy_Camera") } catch (_: Throwable) { null }
    try {
        if (uri != null && Desktop.isDesktopSupported()) {
            Desktop.getDesktop().browse(uri)
            return
        }
    } catch (_: Throwable) {
        // ignore
    }
}
