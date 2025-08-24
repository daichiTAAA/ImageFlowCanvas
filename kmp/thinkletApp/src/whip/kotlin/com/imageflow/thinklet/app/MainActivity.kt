package com.imageflow.thinklet.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import org.webrtc.*

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { ThinkletWhipApp(this) }
    }
}

// MediaMTX expects WHIP at "/<path>/whip" (not "/whip/<path>")
private fun normalizeWhipPostUrl(raw: String): String {
    val parsed = raw.toHttpUrlOrNull()
    if (parsed != null) {
        // rebuild path segments: remove leading "whip"/"whep" if present, ensure trailing "whip"
        val segs = parsed.encodedPathSegments.filter { it.isNotEmpty() }.toMutableList()
        if (segs.firstOrNull() == "whip" || segs.firstOrNull() == "whep") {
            segs.removeAt(0)
        }
        if (segs.lastOrNull() != "whip") {
            segs.add("whip")
        }
        val b = parsed.newBuilder().encodedPath("/")
        segs.forEach { b.addPathSegment(it) }
        return b.build().toString()
    }
    // Fallback string handling
    var s = raw.trim()
    // move leading /whip/... to .../whip
    s = s.replace(Regex("/whip/+"), "/")
    s = if (s.endsWith("/whip")) s else if (s.endsWith('/')) s + "whip" else "$s/whip"
    return s
}

private fun extractOrigin(raw: String): String? {
    val u = raw.toHttpUrlOrNull() ?: return null
    val defaultPort = if (u.isHttps) 443 else 80
    val portPart = if (u.port != defaultPort) ":${u.port}" else ""
    return "${u.scheme}://${u.host}$portPart"
}

@Composable
private fun ThinkletWhipApp(activity: ComponentActivity) {
    val context = LocalContext.current
    var hasPermissions by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        val required = listOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
        hasPermissions = required.all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    MaterialTheme { Surface(Modifier.fillMaxSize()) {
        WhipHeadlessScreen(activity, hasPermissions)
    } }
}

@Composable
private fun WhipHeadlessScreen(activity: ComponentActivity, hasPermissions: Boolean) {
    val context = LocalContext.current
    var log by remember { mutableStateOf("Ready.") }
    var isStreaming by remember { mutableStateOf(false) }
    val controller = remember { WhipController(activity) }
    val configuredUrl = remember { AppConfig.getWhipUrl(context) }
    val autoStart = remember { AppConfig.getAutoStart(context) }

    // Connectivity test states
    var testUrlTest by remember { mutableStateOf("") }
    var testResultTest by remember { mutableStateOf("") }

    LaunchedEffect(hasPermissions, configuredUrl, autoStart) {
        if (autoStart && hasPermissions && !isStreaming && configuredUrl.isNotBlank()) {
            controller.start(configuredUrl,
                onLog = { log = it },
                onError = { log = it },
                onConnected = { isStreaming = true },
                onDisconnected = { isStreaming = false })
        } else if (!hasPermissions) {
            log = "権限が未許可です (adb で事前付与してください)"
        }
    }

    // Minimal status-only UI for debugging; THINKLETでは表示されません
    Column(Modifier.fillMaxSize().padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("THINKLET ライブ配信 (WHIP)")
        val postUrl = remember(configuredUrl) { normalizeWhipPostUrl(configuredUrl) }
        Text("設定URL: ${configuredUrl}")
        Text("POST先URL: ${postUrl}")
        Text("状態: ${log}")
        if (isStreaming) Text("配信中") else Text("待機中")

        // Connectivity test display
        Text("接続テスト: whip/test")
        if (testUrlTest.isNotBlank()) Text("URL: ${testUrlTest}")
        if (testResultTest.isNotBlank()) Text("結果: ${testResultTest}")

        Button(onClick = {
            // Derive test URL against server origin
            val origin = extractOrigin(configuredUrl) ?: configuredUrl
            val urlTest = origin.trimEnd('/') + "/whip/test/"

            testUrlTest = urlTest
            testResultTest = ""

            controller.testWhipEndpoint(urlTest) { result ->
                testResultTest = result
            }
        }) { Text("接続テストを実行") }
    }
}

// Previewなし運用のため、Renderer は不要

private class WhipController(private val activity: ComponentActivity) {
    private val eglBase: EglBase = EglBase.create()
    private val http = OkHttpClient()

    private var factory: PeerConnectionFactory? = null
    private var pc: PeerConnection? = null
    private var videoCapturer: VideoCapturer? = null
    private var videoSource: VideoSource? = null
    private var videoTrack: VideoTrack? = null
    private var audioSource: AudioSource? = null
    private var audioTrack: AudioTrack? = null
    private var resourceUrl: String? = null

    private fun ensureFactory() {
        if (factory != null) return
        val initOptions = PeerConnectionFactory.InitializationOptions.builder(activity)
            .setEnableInternalTracer(false).createInitializationOptions()
        PeerConnectionFactory.initialize(initOptions)
        // Wrap encoder factory to advertise/allow only H264
        val baseEncoder = DefaultVideoEncoderFactory(eglBase.eglBaseContext, true, true)
        val encoder = object : VideoEncoderFactory {
            override fun createEncoder(info: VideoCodecInfo): VideoEncoder? {
                return if (info.name.equals("H264", ignoreCase = true)) baseEncoder.createEncoder(info) else null
            }

            override fun getSupportedCodecs(): Array<VideoCodecInfo> {
                return baseEncoder.supportedCodecs.filter { it.name.equals("H264", ignoreCase = true) }.toTypedArray()
            }
        }
        val decoder = DefaultVideoDecoderFactory(eglBase.eglBaseContext)
        factory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(encoder)
            .setVideoDecoderFactory(decoder)
            .createPeerConnectionFactory()
    }

    // Prefer H264 for HLS compatibility; keep RTX for chosen PT
    private fun preferH264(original: String): String {
        val lines = original.split("\r\n", "\n").toMutableList()
        var h264Pt: String? = null
        val keepPts = mutableSetOf<String>()
        // find H264 payload type
        lines.forEach { l ->
            val m = Regex("^a=rtpmap:(\\d+) H264/90000").find(l)
            if (m != null) {
                h264Pt = m.groupValues[1]
                keepPts.add(h264Pt!!)
            }
        }
        if (h264Pt == null) return original // no H264 advertised; do nothing

        // find RTX apt for H264 and keep it too
        lines.forEach { l ->
            val m = Regex("^a=fmtp:(\\d+) apt=${h264Pt}").find(l)
            if (m != null) keepPts.add(m.groupValues[1])
        }

        val out = mutableListOf<String>()
        for (l in lines) {
            when {
                l.startsWith("m=video ") -> {
                    val parts = l.split(" ").toMutableList()
                    if (parts.size > 3) {
                        val header = parts.subList(0, 3).joinToString(" ")
                        val pts = parts.drop(3).filter { keepPts.contains(it) }
                        out.add((listOf(header) + pts).joinToString(" "))
                    } else {
                        out.add(l)
                    }
                }
                l.startsWith("a=rtpmap:") || l.startsWith("a=fmtp:") || l.startsWith("a=rtcp-fb:") -> {
                    val m = Regex("^a=(?:rtpmap|fmtp|rtcp-fb):(\\d+)").find(l)
                    val pt = m?.groupValues?.getOrNull(1)
                    if (pt == null || keepPts.contains(pt)) {
                        out.add(l)
                    }
                }
                else -> out.add(l)
            }
        }
        return out.joinToString("\r\n")
    }

    private fun createCameraCapturer(): VideoCapturer? {
        val enumerator = Camera2Enumerator(activity)
        val deviceNames = enumerator.deviceNames
        deviceNames.firstOrNull { enumerator.isBackFacing(it) }?.let { return enumerator.createCapturer(it, null) }
        return deviceNames.firstOrNull()?.let { enumerator.createCapturer(it, null) }
    }

    fun start(
        url: String,
        onLog: (String) -> Unit,
        onError: (String) -> Unit,
        onConnected: (() -> Unit)? = null,
        onDisconnected: (() -> Unit)? = null,
    ) {
        fun uiLog(msg: String) = activity.runOnUiThread { onLog(msg) }
        fun uiError(msg: String) = activity.runOnUiThread { onError(msg) }
        ensureFactory()
        val f = factory ?: return
        try {
            val surfaceHelper = SurfaceTextureHelper.create("CaptureThread", eglBase.eglBaseContext)
            videoCapturer = createCameraCapturer()
            videoSource = f.createVideoSource(false)
            videoCapturer?.initialize(surfaceHelper, activity, videoSource!!.capturerObserver)
            // Try higher resolution first, then fall back gracefully
            fun tryStartCapture(w: Int, h: Int, fps: Int): Boolean {
                return try { videoCapturer?.startCapture(w, h, fps); true } catch (_: Exception) { false }
            }
            if (!(tryStartCapture(1920, 1080, 30) || tryStartCapture(1280, 720, 30) || tryStartCapture(960, 540, 30))) {
                tryStartCapture(640, 360, 30)
            }
            videoTrack = f.createVideoTrack("video0", videoSource)

            audioSource = f.createAudioSource(MediaConstraints())
            audioTrack = f.createAudioTrack("audio0", audioSource)

            val iceServers = listOf(PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer())
            val rtcConfig = PeerConnection.RTCConfiguration(iceServers).apply { sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN }
            pc = f.createPeerConnection(rtcConfig, object : PeerConnection.Observer {
                override fun onSignalingChange(newState: PeerConnection.SignalingState) {}
                override fun onIceConnectionChange(newState: PeerConnection.IceConnectionState) {}
                override fun onIceConnectionReceivingChange(receiving: Boolean) {}
                override fun onIceGatheringChange(newState: PeerConnection.IceGatheringState) {}
                override fun onIceCandidate(candidate: IceCandidate) {}
                override fun onIceCandidatesRemoved(candidates: Array<IceCandidate>) {}
                override fun onAddStream(stream: MediaStream) {}
                override fun onRemoveStream(stream: MediaStream) {}
                override fun onDataChannel(dc: DataChannel) {}
                override fun onRenegotiationNeeded() {}
                override fun onAddTrack(receiver: RtpReceiver, streams: Array<out MediaStream>) {}
            })

            val transceiverInit = RtpTransceiver.RtpTransceiverInit(RtpTransceiver.RtpTransceiverDirection.SEND_ONLY)
            val vTrans = pc!!.addTransceiver(videoTrack, transceiverInit)
            pc!!.addTransceiver(audioTrack, transceiverInit)

            // Bump up publisher bitrate/framerate for better quality
            try {
                val vSender = vTrans.sender
                val vParams = vSender.parameters
                vParams.encodings?.forEach { enc ->
                    // 4-6 Mbps target for 1080p30; allow downscale if needed
                    enc.maxBitrateBps = 6_000_000
                    enc.minBitrateBps = 800_000
                    enc.maxFramerate = 30
                    enc.scaleResolutionDownBy = 1.0
                }
                vSender.parameters = vParams
            } catch (_: Exception) {
                // ignore if parameters not supported on device
            }

            val constraints = MediaConstraints().apply {
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "false"))
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "false"))
            }
            pc!!.createOffer(object : SdpObserver {
                override fun onCreateSuccess(desc: SessionDescription) {
                    val munged = SessionDescription(desc.type, preferH264(desc.description))
                    pc!!.setLocalDescription(object : SdpObserver {
                        override fun onSetSuccess() {
                            waitForIceGatheringComplete {
                                val offerSdp = pc!!.localDescription?.description ?: return@waitForIceGatheringComplete
                                val mediaType = "application/sdp".toMediaType()
                                val publishUrl = normalizeWhipPostUrl(url)
                                uiLog("Preparing WHIP POST to: $publishUrl (SDP ${offerSdp.length} bytes)")
                                val req = Request.Builder()
                                    .url(publishUrl)
                                    .addHeader("Content-Type", "application/sdp")
                                    .addHeader("Accept", "application/sdp")
                                    .post(RequestBody.create(mediaType, offerSdp.toByteArray()))
                                    .build()
                                Thread {
                                    try {
                                        uiLog("WHIP POST: $publishUrl")
                                        fun doPost(url: String): Pair<Int, String?> {
                                            val r = Request.Builder()
                                                .url(url)
                                                .addHeader("Content-Type", "application/sdp")
                                                .addHeader("Accept", "application/sdp")
                                                .post(RequestBody.create(mediaType, offerSdp.toByteArray()))
                                                .build()
                                            http.newCall(r).execute().use { resp ->
                                                return Pair(resp.code, if (resp.isSuccessful) (resp.body?.string() ?: "") else null).also {
                                                    uiLog("WHIP POST resp: ${resp.code} ${resp.message}")
                                                    val loc = resp.header("Location")
                                                    if (resp.code in listOf(301,302,307,308) && loc != null) {
                                                        val base = url.toHttpUrlOrNull()
                                                        val next = if (base != null) base.resolve(loc)?.toString() else loc
                                                        if (next != null) {
                                                            uiLog("WHIP redirect -> $next")
                                                            val (code2, body2) = doPost(next)
                                                            throw java.lang.RuntimeException("__WHIP_REDIRECT__:${code2}:${body2 ?: ""}")
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        var finalUrl = publishUrl
                                        var code: Int
                                        var answer: String? = null
                                        try {
                                            val (c, a) = doPost(finalUrl)
                                            code = c; answer = a
                                        } catch (e: RuntimeException) {
                                            if (e.message?.startsWith("__WHIP_REDIRECT__:") == true) {
                                                val parts = e.message!!.removePrefix("__WHIP_REDIRECT__:").split(":", limit = 2)
                                                code = parts[0].toInt()
                                                answer = parts.getOrNull(1)
                                            } else throw e
                                        }

                                        // Minimal fallback: try without trailing slash if 404
                                        if (code == 404 && finalUrl.endsWith('/')) {
                                            finalUrl = finalUrl.dropLast(1)
                                            uiLog("WHIP retry (no trailing /): $finalUrl")
                                            val (c2, a2) = doPost(finalUrl); code = c2; answer = a2
                                        }

                                        if (code < 200 || code >= 300) {
                                            uiError("WHIP POST failed: $code")
                                            return@Thread
                                        }
                                        resourceUrl = null
                                        pc!!.setRemoteDescription(object : SdpObserver {
                                                override fun onSetSuccess() { uiLog("WHIP connected"); onConnected?.invoke() }
                                                override fun onSetFailure(p0: String?) { uiError("setRemoteDescription: $p0") }
                                                override fun onCreateSuccess(p0: SessionDescription?) {}
                                                override fun onCreateFailure(p0: String?) {}
                                            }, SessionDescription(SessionDescription.Type.ANSWER, answer ?: ""))
                                    } catch (e: Exception) {
                                        uiError("WHIP signaling error: ${e::class.java.simpleName}: ${e.message}")
                                        onDisconnected?.invoke()
                                    }
                                }.start()
                            }
                        }
                        override fun onSetFailure(p0: String?) { uiError("setLocalDescription: $p0") }
                        override fun onCreateSuccess(p0: SessionDescription?) {}
                        override fun onCreateFailure(p0: String?) {}
                    }, desc)
                }
                override fun onCreateFailure(p0: String?) { uiError("createOffer: $p0") }
                override fun onSetSuccess() {}
                override fun onSetFailure(p0: String?) {}
            }, constraints)
        } catch (e: Exception) {
            uiError("start error: ${e::class.java.simpleName}: ${e.message}")
            onDisconnected?.invoke()
        }
    }

    fun stop(onLog: (String) -> Unit) {
        try {
            resourceUrl?.let { res ->
                try { http.newCall(Request.Builder().url(res).delete().build()).execute().close() } catch (_: Exception) {}
            }
            pc?.close(); pc = null
            try { videoCapturer?.stopCapture() } catch (_: Exception) {}
            videoCapturer?.dispose(); videoCapturer = null
            videoSource?.dispose(); videoSource = null
            audioSource?.dispose(); audioSource = null
            videoTrack = null; audioTrack = null
            onLog("WHIP disconnected")
        } catch (_: Exception) {}
    }

    private fun waitForIceGatheringComplete(then: () -> Unit) {
        val connection = pc ?: return
        // Some webrtc artifacts (including those pulled transitively by Stream SDK)
        // don't expose addIceGatheringStateChangedObserver. Poll until COMPLETE.
        var elapsed = 0L
        fun check() {
            if (connection.iceGatheringState() == PeerConnection.IceGatheringState.COMPLETE) {
                then()
            } else {
                activity.window.decorView.postDelayed({
                    elapsed += 100
                    if (elapsed >= 2000) {
                        // fallback: proceed even if not COMPLETE
                        then()
                    } else {
                        check()
                    }
                }, 100)
            }
        }
        check()
    }

    // publish URL 正規化は start() 内で行うため、ここでは不要

    fun testWhipEndpoint(url: String, onResult: (String) -> Unit) {
        Thread {
            try {
                val req = Request.Builder().url(url).get().build()
                http.newCall(req).execute().use { resp ->
                    val server = resp.header("Server") ?: ""
                    val loc = resp.header("Location") ?: ""
                    val msg = "HTTP ${resp.code} ${resp.message} Server=${server} Location=${loc}"
                    activity.runOnUiThread { onResult(msg) }
                }
            } catch (e: Exception) {
                activity.runOnUiThread { onResult("connect error: ${e.message}") }
            }
        }.start()
    }
}
