package com.imageflow.kmp.platform

internal class IosCameraController : CameraController {
    override fun start() { println("[IosCameraController] start: initializing AVFoundation (stub)") }
    override fun stop() { println("[IosCameraController] stop: releasing AVFoundation (stub)") }
}

actual fun provideCameraController(): CameraController = IosCameraController()
