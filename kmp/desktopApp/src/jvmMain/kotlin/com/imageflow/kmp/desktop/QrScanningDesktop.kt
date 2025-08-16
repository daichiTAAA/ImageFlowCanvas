package com.imageflow.kmp.desktop

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Keyboard
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.imageflow.kmp.models.QrScanResult
import com.imageflow.kmp.qr.DefaultBarcodeDecoder
import com.imageflow.kmp.qr.DecodedProductInfo
import com.imageflow.kmp.qr.ValidationResult
import com.imageflow.kmp.qr.ValidationError
import com.google.zxing.*
import com.google.zxing.common.HybridBinarizer
import com.google.zxing.client.j2se.BufferedImageLuminanceSource
import org.bytedeco.javacv.FFmpegFrameGrabber
import org.bytedeco.javacv.Frame
import org.bytedeco.javacv.Java2DFrameConverter
import javax.swing.JPanel
import java.awt.BorderLayout
import java.awt.image.BufferedImage
import org.bytedeco.ffmpeg.global.avutil.AV_PIX_FMT_0RGB

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun QrScanningScreenDesktop(
    isScanning: Boolean,
    lastScanResult: QrScanResult?,
    onBackClick: () -> Unit,
    onManualEntryClick: () -> Unit,
    onRawScanned: (String) -> Unit,
    onAcceptResult: (QrScanResult) -> Unit,
    onRetryClick: () -> Unit,
) {
    var grabber by remember { mutableStateOf<FFmpegFrameGrabber?>(null) }
    var imagePanel by remember { mutableStateOf<ImagePanel?>(null) }
    var latestFrame by remember { mutableStateOf<java.awt.image.BufferedImage?>(null) }

    // Initialize webcam lazily when screen enters composition
    LaunchedEffect(Unit) {
        // Try to find a working camera index (0..5)
        val working = findWorkingGrabberAvFoundation()
        grabber = working
        if (working != null) {
            imagePanel = ImagePanel()
        }
    }

    // Ensure resources are released
    DisposableEffect(Unit) {
        onDispose {
            try { grabber?.stop() } catch (_: Throwable) {}
            try { grabber?.release() } catch (_: Throwable) {}
        }
    }

    // Control to prevent spamming decode
    var emitted by remember { mutableStateOf(false) }
    LaunchedEffect(lastScanResult) {
        if (lastScanResult == null) emitted = false
    }

    // QR decoding loop using ZXing
    LaunchedEffect(isScanning, grabber) {
        if (!isScanning || grabber == null) return@LaunchedEffect
        val reader = MultiFormatReader().apply {
            val hints = mapOf(
                DecodeHintType.POSSIBLE_FORMATS to listOf(BarcodeFormat.QR_CODE, BarcodeFormat.DATA_MATRIX, BarcodeFormat.AZTEC, BarcodeFormat.PDF_417),
                DecodeHintType.TRY_HARDER to true
            )
            setHints(hints)
        }
        val converter = Java2DFrameConverter()
        while (isScanning) {
            if (!emitted) {
                try {
                    val frame: Frame? = try { grabber?.grab() } catch (_: Throwable) { null }
                    val img = frame?.let { converter.convert(it) }
                    if (img != null) {
                        val rgb = ensureRgb(img)
                        latestFrame = rgb
                        imagePanel?.setImage(rgb)
                        val source = BufferedImageLuminanceSource(rgb)
                        val bitmap = BinaryBitmap(HybridBinarizer(source))
                        val result = reader.decodeWithState(bitmap)
                        val text = result.text
                        if (!text.isNullOrBlank()) {
                            emitted = true
                            onRawScanned(text)
                        }
                    }
                } catch (_: NotFoundException) {
                    // no code in frame
                } catch (_: Throwable) {
                    // ignore decode errors
                }
            }
            kotlinx.coroutines.delay(250)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("QRコードスキャン", color = Color.White) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "戻る", tint = Color.White)
                    }
                },
                actions = {
                    IconButton(onClick = onManualEntryClick) {
                        Icon(Icons.Filled.Keyboard, contentDescription = "手動入力", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Black.copy(alpha = 0.7f))
            )
        },
        containerColor = Color.Black
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color.Black)
        ) {
            // Camera preview area (SwingPanel hosting WebcamPanel)
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                SwingPanelHost(imagePanel)

                if (grabber == null) {
                    Box(modifier = Modifier.align(Alignment.Center)) {
                        Text("カメラ初期化に失敗しました", color = Color.White)
                    }
                }
            }

            // Show scan result (success or differences when invalid)
            lastScanResult?.let { result ->
                if (result.success && result.productInfo != null) {
                    ResultCardDesktop(result, onAccept = { onAcceptResult(result) }, onRetry = onRetryClick)
                } else {
                    // Show obtained data and how it differs from the required format
                    val decoder = remember { DefaultBarcodeDecoder() }
                    val decoded = remember(result.rawData) { decoder.decode(result.rawData) }
                    val validation = remember(decoded) { decoder.validate(decoded) }
                    DifferenceCard(raw = result.rawData, decoded = decoded, validation = validation, onRetry = onRetryClick)
                }
            }
        }
    }
}

@Composable
private fun SwingPanelHost(panel: JPanel?) {
    // Host a root container and swap children when panel changes
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

private class ImagePanel : JPanel() {
    @Volatile private var image: java.awt.image.BufferedImage? = null
    fun setImage(img: java.awt.image.BufferedImage) {
        this.image = img
        repaint()
    }
    override fun paintComponent(g: java.awt.Graphics) {
        super.paintComponent(g)
        val img = image ?: return
        val g2 = g as java.awt.Graphics2D
        // Fit image to panel keeping aspect ratio
        val panelW = width.toDouble()
        val panelH = height.toDouble()
        val imgW = img.width.toDouble()
        val imgH = img.height.toDouble()
        val scale = kotlin.math.min(panelW / imgW, panelH / imgH)
        val drawW = (imgW * scale).toInt()
        val drawH = (imgH * scale).toInt()
        val x = (panelW - drawW) / 2.0
        val y = (panelH - drawH) / 2.0
        g2.drawImage(img, x.toInt(), y.toInt(), drawW, drawH, null)
    }
}

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

// Try to initialize a working grabber by probing device indices
private fun findWorkingGrabberAvFoundation(): FFmpegFrameGrabber? {
    // Common avfoundation device strings to try
    val candidates = listOf("0", "1", "0:0", "1:0")
    for (dev in candidates) {
        try {
            val g = FFmpegFrameGrabber(dev)
            g.format = "avfoundation"
            g.frameRate = 30.0
            g.imageWidth = 1280
            g.imageHeight = 720
            g.pixelFormat = AV_PIX_FMT_0RGB
            // Try start
            g.start()
            val frame = g.grab()
            if (frame != null) {
                return g // keep started
            }
            g.stop()
            g.release()
        } catch (_: Throwable) {
            // try next device string
        }
    }
    return null
}

@Composable
private fun ResultCardDesktop(
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
        Column(modifier = Modifier.padding(16.dp)) {
            Text("QRコード読み取り成功", color = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(8.dp))
            val p = result.productInfo!!
            Text("製品タイプ: ${p.productType}")
            Text("機番: ${p.machineNumber}")
            Text("指図番号: ${p.workOrderId}")
            Text("指示番号: ${p.instructionId}")
            Text("生産年月日: ${p.productionDate}")
            Text("月連番: ${p.monthlySequence}")
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onRetry, modifier = Modifier.weight(1f)) { Text("再スキャン") }
                Button(onClick = onAccept, modifier = Modifier.weight(1f)) { Text("この製品を選択") }
            }
        }
    }
}

@Composable
private fun DifferenceCard(
    raw: String,
    decoded: DecodedProductInfo,
    validation: ValidationResult,
    onRetry: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("QRコードの内容を認識しましたが、指定形式と一致しません。", color = MaterialTheme.colorScheme.error)
            Spacer(Modifier.height(8.dp))
            Text("取得データ (生データ):")
            Text(raw, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(8.dp))
            Text("指定フォーマット:")
            Text("workOrderId,instructionId,productType,machineNumber,productionDate(YYYY-MM-DD),monthlySequence")
            Spacer(Modifier.height(8.dp))
            Text("解析されたフィールド:")
            val fields = listOf(
                "workOrderId" to (decoded.workOrderId ?: "(なし)"),
                "instructionId" to (decoded.instructionId ?: "(なし)"),
                "productType" to (decoded.productType ?: "(なし)"),
                "machineNumber" to (decoded.machineNumber ?: "(なし)"),
                "productionDate" to (decoded.productionDate ?: "(なし)"),
                "monthlySequence" to (decoded.monthlySequence?.toString() ?: "(なし)")
            )
            fields.forEach { (k, v) -> Text("- $k: $v") }
            if (validation.errors.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Text("不一致の内容:")
                validation.errors.forEach { e: ValidationError ->
                    Text("- ${e.field}: ${e.message}")
                }
            }
            Spacer(Modifier.height(12.dp))
            Button(onClick = onRetry, modifier = Modifier.fillMaxWidth()) { Text("再試行") }
        }
    }
}
