package com.imageflow.kmp.desktop

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.awt.SwingPanel
import io.grpc.ManagedChannel
import io.grpc.ManagedChannelBuilder
import imageflow.v1.CameraStreamProcessorGrpcKt
import imageflow.v1.CameraStream
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest
import java.awt.BorderLayout
import java.awt.image.BufferedImage
import java.io.ByteArrayOutputStream
import javax.imageio.ImageIO
import javax.swing.JPanel
import org.bytedeco.javacv.FFmpegFrameGrabber
import org.bytedeco.javacv.Java2DFrameConverter
import org.bytedeco.javacv.Frame
import org.bytedeco.ffmpeg.global.avutil.AV_PIX_FMT_0RGB
import javax.swing.SwingUtilities

@Composable
fun RealtimeInspectionDesktop(
    grpcHost: String,
    grpcPort: Int,
    pipelineId: String = "default",
    modifier: Modifier = Modifier
) {
    var grabber by remember { mutableStateOf<FFmpegFrameGrabber?>(null) }
    var imagePanel by remember { mutableStateOf<RtImagePanel?>(null) }
    var channel by remember { mutableStateOf<ManagedChannel?>(null) }
    var running by remember { mutableStateOf(true) } // 自動開始
    var stats by remember { mutableStateOf(Stats()) }

    DisposableEffect(Unit) {
        onDispose {
            try { grabber?.stop() } catch (_: Throwable) {}
            try { grabber?.release() } catch (_: Throwable) {}
            try { channel?.shutdownNow() } catch (_: Throwable) {}
        }
    }

    Column(modifier = modifier.fillMaxWidth().background(Color.Black)) {
        Row(Modifier.fillMaxWidth().padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("gRPC ${grpcHost}:${grpcPort}", color = Color.White)
            Spacer(Modifier.width(16.dp))
            Text("Frames: ${stats.frames} / Detections: ${stats.lastDetections}", color = Color.LightGray)
            Spacer(Modifier.weight(1f))
            OutlinedButton(onClick = { running = !running }) { Text(if (running) "停止" else "開始") }
        }

        Box(Modifier.fillMaxWidth().height(360.dp).background(Color.Black)) {
            SwingPanel(factory = {
                RtImagePanel().also { imagePanel = it }
            }, update = { panel ->
                // no-op
            })
        }
    }

    LaunchedEffect(running) {
        if (!running) return@LaunchedEffect
        // 重い処理はIOに退避（UIブロック回避）
        withContext(Dispatchers.IO) {
            channel = ManagedChannelBuilder.forAddress(grpcHost, grpcPort)
                .usePlaintext()
                .build()
            val stub = CameraStreamProcessorGrpcKt.CameraStreamProcessorCoroutineStub(channel!!)

            val g = openBestAvFoundationGrabber() ?: FFmpegFrameGrabber("0").apply {
                format = "avfoundation"
                imageWidth = 1280; imageHeight = 720
                audioChannels = 0; pixelFormat = AV_PIX_FMT_0RGB
                setOption("probesize", "5000000")
                setOption("analyzeduration", "5000000")
                try { start() } catch (_: Throwable) {}
            }
            grabber = g
            val converter = Java2DFrameConverter()
            // Warm-up: drop initial frames to stabilize timebase
            try {
                repeat(10) { _ -> g?.grabImage() }
            } catch (_: Throwable) {}

            val requests = kotlinx.coroutines.flow.MutableSharedFlow<CameraStream.VideoFrame>(extraBufferCapacity = 2)
            val recvJob = launch(Dispatchers.IO) {
                try {
                    stub.processVideoStream(requests).collect { resp ->
                        withContext(Dispatchers.Main) { stats = stats.copy(lastDetections = resp.detectionsCount) }
                    }
                } catch (_: Throwable) {}
            }

            try {
                while (isActive && running) {
                    val frame: Frame? = try { g?.grabImage() } catch (_: Throwable) { null }
                    val img = frame?.let { converter.convert(it) } ?: continue
                    SwingUtilities.invokeLater { imagePanel?.setImage(img) }
                    val bytes = encodeJpeg(img)
                    val meta = CameraStream.VideoMetadata.newBuilder()
                        .setSourceId("desktop-usb-0")
                        .setWidth(img.width)
                        .setHeight(img.height)
                        .setPipelineId(pipelineId)
                        .build()
                    val vf = CameraStream.VideoFrame.newBuilder()
                        .setFrameData(com.google.protobuf.ByteString.copyFrom(bytes))
                        .setTimestampMs(System.currentTimeMillis())
                        .setMetadata(meta)
                        .build()
                    requests.tryEmit(vf)
                    withContext(Dispatchers.Main) { stats = stats.copy(frames = stats.frames + 1) }
                    delay(1000)
                }
            } finally {
                recvJob.cancel()
                try { g?.stop() } catch (_: Throwable) {}
                try { g?.release() } catch (_: Throwable) {}
                try { channel?.shutdownNow() } catch (_: Throwable) {}
            }
        }
    }
}

private fun encodeJpeg(img: BufferedImage): ByteArray {
    val baos = ByteArrayOutputStream()
    ImageIO.write(img, "jpg", baos)
    return baos.toByteArray()
}

private class RtImagePanel : JPanel(BorderLayout()) {
    @Volatile private var image: BufferedImage? = null
    fun setImage(img: BufferedImage) { image = img; repaint() }
    override fun paintComponent(g: java.awt.Graphics) {
        super.paintComponent(g)
        val img = image ?: return
        val g2 = g as java.awt.Graphics2D
        val panelW = width.toDouble()
        val panelH = height.toDouble()
        val imgW = img.width.toDouble()
        val imgH = img.height.toDouble()
        val scale = kotlin.math.min(panelW / imgW, panelH / imgH)
        val drawW = (imgW * scale).toInt()
        val drawH = (imgH * scale).toInt()
        val x = ((panelW - drawW) / 2.0).toInt()
        val y = ((panelH - drawH) / 2.0).toInt()
        g2.drawImage(img, x, y, drawW, drawH, null)
    }
}

private data class Stats(
    val frames: Int = 0,
    val lastDetections: Int = 0
)

private fun openBestAvFoundationGrabber(): FFmpegFrameGrabber? {
    val devices = listOf("0", "1", "0:0", "1:0")
    // Try common supported resolutions and exact fps values seen in the log
    val resolutions = listOf(1280 to 720, 640 to 480, 800 to 600, 1024 to 576)
    val fpsCandidates = listOf(30.000030, 60.000240, 25.0, 15.000015, 10.0, 5.0)
    for (dev in devices) {
        for ((w, h) in resolutions) {
            for (fps in fpsCandidates) {
                try {
                    val g = FFmpegFrameGrabber(dev)
                    g.format = "avfoundation"
                    g.imageWidth = w
                    g.imageHeight = h
                    g.audioChannels = 0
                    g.pixelFormat = AV_PIX_FMT_0RGB
                    // Hint both via option and property to avoid 29.97選択
                    g.setOption("framerate", String.format(java.util.Locale.US, "%.6f", fps))
                    g.frameRate = fps
                    g.setOption("probesize", "5000000")
                    g.setOption("analyzeduration", "5000000")
                    g.start()
                    // Grab a couple frames to stabilize
                    var ok = false
                    repeat(3) {
                        val fr = try { g.grabImage() } catch (_: Throwable) { null }
                        if (fr != null) ok = true
                    }
                    if (ok) return g
                    g.stop(); g.release()
                } catch (_: Throwable) {
                    // try next mode
                }
            }
        }
    }
    return null
}
