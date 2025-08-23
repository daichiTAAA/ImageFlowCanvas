package com.imageflow.kmp.platform

actual fun listAvailableCameras(): List<CameraDeviceInfo> {
    // Stub for iOS target (not currently used)
    return listOf(CameraDeviceInfo("default", "Default Camera"))
}

