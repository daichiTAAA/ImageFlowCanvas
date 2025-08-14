package com.imageflow.kmp.platform

actual object PlatformDefaults {
    // Android emulator can reach host via 10.0.2.2
    actual fun defaultApiBase(): String = "http://10.0.2.2:8000/api/v1"
}

