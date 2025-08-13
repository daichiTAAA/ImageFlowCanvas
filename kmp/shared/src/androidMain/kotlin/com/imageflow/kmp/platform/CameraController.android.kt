package com.imageflow.kmp.platform

import com.imageflow.kmp.models.QrScanResult
import com.imageflow.kmp.qr.DecodedProductInfo
import com.imageflow.kmp.qr.toProductInfo
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.runBlocking

// Enhanced camera controller interface with mobile inspection features
// Based on F-021-1 QR scanning and F-022 image capture requirements
actual interface CameraController {
    actual fun start()
    actual fun stop()
    
    // QR code scanning functionality
    fun startQrScanning(): Flow<QrScanResult>
    fun stopQrScanning()
    
    // Image capture for inspection
    suspend fun captureImage(outputPath: String): Boolean
    suspend fun captureImageWithMetadata(outputPath: String, metadata: Map<String, String>): Boolean
    
    // Video recording for inspection
    suspend fun startVideoRecording(outputPath: String): Boolean
    suspend fun stopVideoRecording(): Boolean
    
    // Camera configuration
    fun setTorchEnabled(enabled: Boolean)
    fun setZoomLevel(zoomLevel: Float)
    fun isTorchAvailable(): Boolean
    fun getMaxZoomLevel(): Float
    
    // Preview and focus
    fun setPreviewSurface(surface: Any?)
    fun focusAt(x: Float, y: Float)
    fun autoFocus()
    
    // Camera state
    fun isStarted(): Boolean
    fun isQrScanningActive(): Boolean
    fun isRecording(): Boolean
}
