package com.imageflow.kmp.platform

actual object PlatformDefaults {
    // iOS Simulator can reach host via localhost
    actual fun defaultApiBase(): String = "http://localhost:8000/v1"
}
