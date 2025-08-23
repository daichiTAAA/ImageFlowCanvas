package com.imageflow.kmp.platform

data class CameraDeviceInfo(
    val id: String,
    val label: String,
)

expect fun listAvailableCameras(): List<CameraDeviceInfo>

