package com.imageflow.kmp.platform

import org.bytedeco.javacv.FFmpegFrameGrabber

actual fun listAvailableCameras(): List<CameraDeviceInfo> {
    // Enumerate AVFoundation video devices by invoking FFmpeg device list and parsing stderr
    // Primary: invoke external ffmpeg to list devices and parse stderr
    val all = runCatching {
        val candidates = listOf("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg")
        var out: String? = null
        for (bin in candidates) {
            try {
                val pb = ProcessBuilder(bin, "-f", "avfoundation", "-list_devices", "true", "-i", "")
                pb.redirectErrorStream(false)
                val p = pb.start()
                val err = p.errorStream.bufferedReader(Charsets.UTF_8).readText()
                // consume stdout too (usually empty)
                runCatching { p.inputStream.bufferedReader(Charsets.UTF_8).readText() }
                // wait but cap at ~2s
                runCatching { p.waitFor(2, java.util.concurrent.TimeUnit.SECONDS) }
                if (err.isNotBlank()) { out = err; break }
            } catch (_: Throwable) { }
        }
        out ?: ""
    }.getOrDefault("")
    println("[CameraCatalog] Raw device listing length: ${all.length}")
    // Print just the lines that look related to avfoundation
    all.lineSequence().filter { it.contains("AVFoundation") }.forEach { ln ->
        println("[CameraCatalog] raw: ${ln}")
    }
    val devices = mutableListOf<CameraDeviceInfo>()
    var inVideo = false
    all.lineSequence().forEach { raw ->
        val line = raw.trim()
        if (line.contains("AVFoundation video devices:")) { inVideo = true; return@forEach }
        if (inVideo && line.contains("AVFoundation audio devices:")) { inVideo = false; return@forEach }
        if (inVideo) {
            // Accept lines like: "[AVFoundation indev @ 0x...] [1] Device Name"
            val m = Regex(".*\\[(\\d+)\\]\\s+(.+)").find(line)
            if (m != null) {
                val name = m.groupValues[2].trim()
                // Filter out screen capture pseudo-devices
                if (!name.contains("Capture screen", ignoreCase = true)) {
                    println("[CameraCatalog] parsed device: ${name}")
                    devices += CameraDeviceInfo(id = name, label = name)
                }
            }
        }
    }
    if (devices.isNotEmpty()) {
        println("[CameraCatalog] devices found: ${devices.size}")
        return devices
    }
    println("[CameraCatalog] No devices parsed; returning Default Camera fallback")
    // Fallback when no devices could be parsed
    return listOf(CameraDeviceInfo(id = "Default Camera", label = "Default Camera"))
}
