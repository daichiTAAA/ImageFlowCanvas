package com.imageflow.kmp.platform

expect interface FileManager {
    fun save(path: String, bytes: ByteArray)
}

