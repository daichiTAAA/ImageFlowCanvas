package com.imageflow.kmp.platform

import android.util.Log

private const val TAG = "AndroidCameraController"

internal class AndroidCameraController : CameraController {
    override fun start() {
        // Sketch: Here you would initialize CameraX/Camera2 pipeline
        Log.d(TAG, "start: initializing camera preview/recording pipeline (stub)")
    }

    override fun stop() {
        Log.d(TAG, "stop: releasing camera resources (stub)")
    }
}

actual fun provideCameraController(): CameraController = AndroidCameraController()

