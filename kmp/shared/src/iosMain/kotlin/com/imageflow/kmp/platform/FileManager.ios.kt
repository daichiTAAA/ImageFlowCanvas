package com.imageflow.kmp.platform

actual interface FileManager {
    actual fun save(path: String, bytes: ByteArray)
}

