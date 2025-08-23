package com.imageflow.kmp.desktop

import org.bytedeco.javacv.FFmpegFrameGrabber
import java.io.ByteArrayOutputStream
import java.io.PrintStream

fun enumAvFoundationVideoDevices(): List<String> {
    // Capture FFmpeg/avfoundation device listing output from stderr
    val originalErr = System.err
    val baos = ByteArrayOutputStream()
    val ps = PrintStream(baos, true, Charsets.UTF_8)
    try {
        System.setErr(ps)
        val lister = FFmpegFrameGrabber("")
        lister.format = "avfoundation"
        lister.setOption("list_devices", "true")
        try { lister.start() } catch (_: Throwable) {}
        try { lister.stop() } catch (_: Throwable) {}
        try { lister.release() } catch (_: Throwable) {}
    } catch (_: Throwable) {
        // ignore
    } finally {
        try { ps.flush() } catch (_: Throwable) {}
        try { System.setErr(originalErr) } catch (_: Throwable) {}
        try { ps.close() } catch (_: Throwable) {}
    }
    val all = baos.toString(Charsets.UTF_8)
    val result = mutableListOf<String>()
    var inVideo = false
    all.lineSequence().forEach { raw ->
        val line = raw.trim()
        if (line.contains("AVFoundation video devices:")) { inVideo = true; return@forEach }
        if (inVideo && line.contains("AVFoundation audio devices:")) { inVideo = false; return@forEach }
        if (inVideo) {
            val m = Regex("\\[(\\d+)\\] (.+)").find(line)
            if (m != null) {
                val name = m.groupValues[2].trim()
                result += name
            }
        }
    }
    return result
}

fun resolveAvFoundationIndexByName(targetName: String): Int? {
    val devices = enumAvFoundationVideoDevices()
    val idx = devices.indexOfFirst { it == targetName }
    return if (idx >= 0) idx else null
}

