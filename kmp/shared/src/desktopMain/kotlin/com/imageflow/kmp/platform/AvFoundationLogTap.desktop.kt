package com.imageflow.kmp.platform

import java.io.OutputStream
import java.io.PrintStream
import java.nio.charset.StandardCharsets

object AvFoundationLogTap {
    @Volatile private var installed = false
    private lateinit var origErr: PrintStream
    private lateinit var tapErr: PrintStream
    private val ring = StringBuilder(32 * 1024)
    private const val MAX = 256 * 1024

    @Synchronized fun installIfNeeded() {
        if (installed) return
        try {
            origErr = System.err
            val tee = object : OutputStream() {
                override fun write(b: Int) {
                    try { origErr.write(b) } catch (_: Throwable) {}
                    synchronized(ring) {
                        ring.append(b.toChar())
                        if (ring.length > MAX) ring.delete(0, ring.length - MAX)
                    }
                }
                override fun write(b: ByteArray, off: Int, len: Int) {
                    try { origErr.write(b, off, len) } catch (_: Throwable) {}
                    val s = String(b, off, len, StandardCharsets.UTF_8)
                    synchronized(ring) {
                        ring.append(s)
                        if (ring.length > MAX) ring.delete(0, ring.length - MAX)
                    }
                }
            }
            tapErr = PrintStream(tee, true, "UTF-8")
            System.setErr(tapErr)
            installed = true
        } catch (_: Throwable) {
            // ignore
        }
    }

    fun snapshot(): String = synchronized(ring) { ring.toString() }
}

