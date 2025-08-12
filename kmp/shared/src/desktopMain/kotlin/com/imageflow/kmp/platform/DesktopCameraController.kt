package com.imageflow.kmp.platform

internal class DesktopCameraController : CameraController {
    override fun start() {
        println("[DesktopCameraController] start: initializing desktop capture (stub)")
    }
    override fun stop() {
        println("[DesktopCameraController] stop: releasing desktop capture (stub)")
    }
}

actual fun provideCameraController(): CameraController = DesktopCameraController()
