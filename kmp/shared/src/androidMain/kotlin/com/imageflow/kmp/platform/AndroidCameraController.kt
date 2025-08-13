package com.imageflow.kmp.platform

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.Recorder
import androidx.camera.video.VideoCapture
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.imageflow.kmp.models.*
import com.imageflow.kmp.qr.DefaultBarcodeDecoder
import com.imageflow.kmp.qr.toProductInfo
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

private const val TAG = "AndroidCameraController"

internal class AndroidCameraController(
    private val context: Context,
    private val lifecycleOwner: LifecycleOwner
) : CameraController {
    
    private var cameraProvider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var preview: Preview? = null
    private var imageCapture: ImageCapture? = null
    private var videoCapture: VideoCapture<Recorder>? = null
    private var imageAnalyzer: ImageAnalysis? = null
    
    private val cameraExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private var previewView: PreviewView? = null
    
    private val qrDecoder = DefaultBarcodeDecoder()
    private val _qrScanResults = MutableSharedFlow<QrScanResult>()
    private var isQrScanningEnabled = false
    private var isStarted = false
    private var isRecordingVideo = false
    
    override fun start() {
        if (isStarted) return
        
        Log.d(TAG, "Starting camera initialization")
        
        if (!hasRequiredPermissions()) {
            Log.e(TAG, "Camera permissions not granted")
            return
        }
        
        try {
            val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
            cameraProviderFuture.addListener({
                try {
                    cameraProvider = cameraProviderFuture.get()
                    setupCamera()
                    isStarted = true
                    Log.d(TAG, "Camera started successfully")
                } catch (e: Exception) {
                    Log.e(TAG, "Camera initialization failed", e)
                }
            }, ContextCompat.getMainExecutor(context))
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start camera", e)
        }
    }

    override fun stop() {
        if (!isStarted) return
        
        try {
            stopQrScanning()
            if (isRecordingVideo) {
                runBlocking { stopVideoRecording() }
            }
            cameraProvider?.unbindAll()
            cameraExecutor.shutdown()
            isStarted = false
            Log.d(TAG, "Camera stopped successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping camera", e)
        }
    }
    
    override fun startQrScanning(): Flow<QrScanResult> {
        if (!isStarted) {
            Log.w(TAG, "Camera not started, cannot begin QR scanning")
            return _qrScanResults.asSharedFlow()
        }
        
        isQrScanningEnabled = true
        setupImageAnalyzer()
        Log.d(TAG, "QR scanning started")
        return _qrScanResults.asSharedFlow()
    }
    
    override fun stopQrScanning() {
        isQrScanningEnabled = false
        Log.d(TAG, "QR scanning stopped")
    }
    
    override suspend fun captureImage(outputPath: String): Boolean {
        return captureImageWithMetadata(outputPath, emptyMap())
    }
    
    override suspend fun captureImageWithMetadata(outputPath: String, metadata: Map<String, String>): Boolean {
        if (!isStarted || imageCapture == null) {
            Log.e(TAG, "Camera not ready for image capture")
            return false
        }
        
        return try {
            val outputFile = File(outputPath)
            val outputOptions = ImageCapture.OutputFileOptions.Builder(outputFile)
                .apply {
                    metadata.forEach { (key, value) ->
                        // Add metadata to EXIF if needed
                    }
                }
                .build()
            
            var captureSuccess = false
            imageCapture?.takePicture(
                outputOptions,
                ContextCompat.getMainExecutor(context),
                object : ImageCapture.OnImageSavedCallback {
                    override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                        captureSuccess = true
                        Log.d(TAG, "Image saved successfully to $outputPath")
                    }
                    
                    override fun onError(exception: ImageCaptureException) {
                        Log.e(TAG, "Image capture failed", exception)
                        captureSuccess = false
                    }
                }
            )
            
            // Simple synchronous return for now - in real implementation, use coroutines properly
            captureSuccess
        } catch (e: Exception) {
            Log.e(TAG, "Error capturing image", e)
            false
        }
    }
    
    override suspend fun startVideoRecording(outputPath: String): Boolean {
        if (!isStarted || videoCapture == null) {
            Log.e(TAG, "Camera not ready for video recording")
            return false
        }
        
        if (isRecordingVideo) {
            Log.w(TAG, "Video recording already in progress")
            return false
        }
        
        return try {
            // VideoCapture implementation would go here
            // This is a simplified stub
            isRecordingVideo = true
            Log.d(TAG, "Video recording started to $outputPath")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Error starting video recording", e)
            false
        }
    }
    
    override suspend fun stopVideoRecording(): Boolean {
        if (!isRecordingVideo) {
            Log.w(TAG, "No video recording in progress")
            return false
        }
        
        return try {
            // Stop video recording implementation
            isRecordingVideo = false
            Log.d(TAG, "Video recording stopped")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping video recording", e)
            false
        }
    }
    
    override fun setTorchEnabled(enabled: Boolean) {
        camera?.cameraControl?.enableTorch(enabled)
    }
    
    override fun setZoomLevel(zoomLevel: Float) {
        camera?.cameraControl?.setZoomRatio(zoomLevel)
    }
    
    override fun isTorchAvailable(): Boolean {
        return camera?.cameraInfo?.hasFlashUnit() ?: false
    }
    
    override fun getMaxZoomLevel(): Float {
        return camera?.cameraInfo?.zoomState?.value?.maxZoomRatio ?: 1.0f
    }
    
    override fun setPreviewSurface(surface: Any?) {
        previewView = surface as? PreviewView
    }
    
    override fun focusAt(x: Float, y: Float) {
        // Implement touch-to-focus
        val meteringPointFactory = previewView?.meteringPointFactory
        val meteringPoint = meteringPointFactory?.createPoint(x, y)
        meteringPoint?.let {
            val focusMeteringAction = FocusMeteringAction.Builder(it).build()
            camera?.cameraControl?.startFocusAndMetering(focusMeteringAction)
        }
    }
    
    override fun autoFocus() {
        camera?.cameraControl?.cancelFocusAndMetering()
    }
    
    override fun isStarted(): Boolean = isStarted
    override fun isQrScanningActive(): Boolean = isQrScanningEnabled
    override fun isRecording(): Boolean = isRecordingVideo
    
    private fun setupCamera() {
        val cameraProvider = this.cameraProvider ?: return
        
        try {
            // Setup preview
            preview = Preview.Builder().build()
            
            // Setup image capture
            imageCapture = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                .build()
            
            // Setup video capture (simplified)
            val recorder = Recorder.Builder().build()
            videoCapture = VideoCapture.withOutput(recorder)
            
            // Setup image analysis for QR scanning
            setupImageAnalyzer()
            
            // Select camera (back camera)
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            
            // Bind use cases to lifecycle
            cameraProvider.unbindAll()
            camera = cameraProvider.bindToLifecycle(
                lifecycleOwner,
                cameraSelector,
                preview,
                imageCapture,
                imageAnalyzer
            )
            
            // Bind preview to PreviewView if available
            previewView?.let { preview?.setSurfaceProvider(it.surfaceProvider) }
            
        } catch (e: Exception) {
            Log.e(TAG, "Camera setup failed", e)
        }
    }
    
    private fun setupImageAnalyzer() {
        imageAnalyzer = ImageAnalysis.Builder()
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
            .apply {
                setAnalyzer(cameraExecutor) { image ->
                    if (isQrScanningEnabled) {
                        analyzeQrCode(image)
                    }
                    image.close()
                }
            }
    }
    
    private fun analyzeQrCode(image: ImageProxy) {
        // This is a simplified QR analysis - in real implementation, 
        // you would use ML Kit or ZXing library
        try {
            // Stub: simulate QR code detection
            val simulatedQrData = "WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1"
            val decodedInfo = qrDecoder.decode(simulatedQrData)
            val productInfo = decodedInfo.toProductInfo()
            
            if (productInfo != null) {
                val scanResult = QrScanResult(
                    success = true,
                    productInfo = productInfo,
                    rawData = simulatedQrData,
                    scanType = ScanType.QR_CODE,
                    confidence = 0.95f,
                    validationStatus = ValidationStatus.VALID
                )
                _qrScanResults.tryEmit(scanResult)
            }
        } catch (e: Exception) {
            Log.e(TAG, "QR analysis failed", e)
        }
    }
    
    private fun hasRequiredPermissions(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }
}

actual fun provideCameraController(): CameraController {
    // This requires a context and lifecycle owner
    // In real implementation, these would be provided through DI
    throw IllegalStateException("AndroidCameraController requires Context and LifecycleOwner - use provideCameraController(context, lifecycleOwner)")
}

// Additional function for Android-specific initialization
fun provideCameraController(context: Context, lifecycleOwner: LifecycleOwner): CameraController {
    return AndroidCameraController(context, lifecycleOwner)
}
