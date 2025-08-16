package com.imageflow.kmp.app

import android.Manifest
import android.content.pm.PackageManager
import android.util.Size
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.FlashlightOff
import androidx.compose.material.icons.filled.FlashlightOn
import androidx.compose.material.icons.filled.Keyboard
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.imageflow.kmp.models.QrScanResult
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun QrScanningScreenAndroid(
    isScanning: Boolean,
    torchEnabled: Boolean,
    lastScanResult: QrScanResult?,
    onBackClick: () -> Unit,
    onTorchToggle: () -> Unit,
    onManualEntryClick: () -> Unit,
    onRawScanned: (String) -> Unit,
    onAcceptResult: (QrScanResult) -> Unit,
    onRetryClick: () -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        hasCameraPermission = granted
    }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    var previewView by remember { mutableStateOf<PreviewView?>(null) }
    var camera by remember { mutableStateOf<Camera?>(null) }
    var analysis by remember { mutableStateOf<ImageAnalysis?>(null) }
    var processing by remember { mutableStateOf(false) }

    LaunchedEffect(torchEnabled, camera) {
        camera?.cameraControl?.enableTorch(torchEnabled)
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
                    IconButton(onClick = onTorchToggle) {
                        Icon(
                            if (torchEnabled) Icons.Filled.FlashlightOff else Icons.Filled.FlashlightOn,
                            contentDescription = if (torchEnabled) "ライトOFF" else "ライトON",
                            tint = if (torchEnabled) Color.Yellow else Color.White
                        )
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
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                AndroidPreview(
                    onPreviewCreated = { pv -> previewView = pv },
                    modifier = Modifier.fillMaxSize()
                )

                // Overlay
                QrOverlay()

                // Instructions placeholder
                Box(modifier = Modifier.align(Alignment.Center)) {
                    if (!hasCameraPermission) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(Icons.Filled.CameraAlt, contentDescription = null, tint = Color.White, modifier = Modifier.size(64.dp))
                            Text("カメラ権限が必要です", color = Color.White)
                        }
                    }
                }
            }

            lastScanResult?.let { result ->
                ResultCard(
                    result = result,
                    onAccept = { onAcceptResult(result) },
                    onRetry = onRetryClick
                )
            }
        }
    }

    // Bind CameraX when permission granted and preview exists
    LaunchedEffect(hasCameraPermission, previewView, isScanning) {
        if (!hasCameraPermission || previewView == null) return@LaunchedEffect

        val cameraProvider = ProcessCameraProvider.getInstance(context).get()
        cameraProvider.unbindAll()

        val preview = Preview.Builder().build().also {
            it.setSurfaceProvider(previewView!!.surfaceProvider)
        }

        val imageAnalysis = ImageAnalysis.Builder()
            .setTargetResolution(Size(1280, 720))
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()

        val scanner = BarcodeScanning.getClient(
            BarcodeScannerOptions.Builder()
                .setBarcodeFormats(
                    com.google.mlkit.vision.barcode.common.Barcode.FORMAT_QR_CODE,
                    com.google.mlkit.vision.barcode.common.Barcode.FORMAT_AZTEC,
                    com.google.mlkit.vision.barcode.common.Barcode.FORMAT_DATA_MATRIX
                )
                .build()
        )

        imageAnalysis.setAnalyzer(ContextCompat.getMainExecutor(context)) { imageProxy ->
            if (!isScanning || processing) {
                imageProxy.close()
                return@setAnalyzer
            }
            val mediaImage = imageProxy.image
            if (mediaImage != null) {
                processing = true
                val rotation = imageProxy.imageInfo.rotationDegrees
                val inputImage = InputImage.fromMediaImage(mediaImage, rotation)
                scanner.process(inputImage)
                    .addOnSuccessListener { barcodes ->
                        val raw = barcodes.firstOrNull()?.rawValue
                        if (raw != null) {
                            onRawScanned(raw)
                        }
                    }
                    .addOnFailureListener {
                        // ignore
                    }
                    .addOnCompleteListener {
                        processing = false
                        imageProxy.close()
                    }
            } else {
                imageProxy.close()
            }
        }

        val selector = CameraSelector.DEFAULT_BACK_CAMERA
        camera = cameraProvider.bindToLifecycle(lifecycleOwner, selector, preview, imageAnalysis)
        analysis = imageAnalysis
    }
}

@Composable
private fun AndroidPreview(onPreviewCreated: (PreviewView) -> Unit, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    AndroidView(
        factory = { ctx -> PreviewView(ctx).also(onPreviewCreated) },
        modifier = modifier
    )
}

@Composable
private fun QrOverlay() {
    Canvas(modifier = Modifier.fillMaxSize()) {
        // Simple corners overlay; kept minimal
        // Could add full implementation as in shared screen if desired
    }
}

@Composable
private fun ResultCard(
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
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = if (result.success) Icons.Filled.CheckCircle else Icons.Filled.Error,
                    contentDescription = null,
                    tint = if (result.success) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (result.success) "QRコード読み取り成功" else "読み取りエラー",
                    fontWeight = FontWeight.Medium,
                    color = if (result.success) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            if (result.success && result.productInfo != null) {
                val p = result.productInfo!!
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("製品コード: ${p.productCode}")
                    Text("機番: ${p.machineNumber}")
                    Text("指図番号: ${p.workOrderId}")
                    Text("指示番号: ${p.instructionId}")
                }
                Spacer(modifier = Modifier.height(16.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = onRetry, modifier = Modifier.weight(1f)) { Text("再スキャン") }
                    Button(onClick = onAccept, modifier = Modifier.weight(1f)) { Text("この製品を選択") }
                }
            } else {
                Text(
                    text = result.errorMessage ?: "QRコードを正しく読み取れませんでした",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Start
                )
                Spacer(modifier = Modifier.height(16.dp))
                Button(onClick = onRetry, modifier = Modifier.fillMaxWidth()) { Text("再試行") }
            }
        }
    }
}
