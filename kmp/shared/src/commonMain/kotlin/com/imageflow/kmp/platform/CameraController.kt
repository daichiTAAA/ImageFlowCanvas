package com.imageflow.kmp.platform

expect interface CameraController {
    fun start()
    fun stop()
}

// Factory to obtain platform camera controller
expect fun provideCameraController(): CameraController
