package com.imageflow.thinklet.app.streaming

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.ComponentActivity
import androidx.core.app.ActivityCompat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.webrtc.*
import java.util.concurrent.TimeUnit

class WhipController(private val activity: ComponentActivity) {
    private val eglBase: EglBase = EglBase.create()
    private val http = OkHttpClient.Builder()
        .callTimeout(8, TimeUnit.SECONDS)
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .build()

    private var factory: PeerConnectionFactory? = null
    private var pc: PeerConnection? = null
    private var videoCapturer: VideoCapturer? = null
    private var videoSource: VideoSource? = null
    private var videoTrack: VideoTrack? = null
    private var audioSource: AudioSource? = null
    private var audioTrack: AudioTrack? = null
    private var resourceUrl: String? = null

    private fun ensurePermissions(decision: StreamingDecision, onError: (String) -> Unit): Boolean {
        val needed = listOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
        val missing = needed.filter {
            ActivityCompat.checkSelfPermission(activity, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            onError("権限が不足しています: ${missing.joinToString()}")
            return false
        }
        ensureFactory(decision)
        return factory != null
    }

    private fun ensureFactory(decision: StreamingDecision) {
        if (factory != null) return
        val initOptions = PeerConnectionFactory.InitializationOptions.builder(activity)
            .setEnableInternalTracer(false)
            .createInitializationOptions()
        PeerConnectionFactory.initialize(initOptions)

        val codecPreference = decision.codecPreference
        val preferredNames = codecPreference.map { it.sdpName.uppercase() }.toSet()

        val baseEncoder = DefaultVideoEncoderFactory(eglBase.eglBaseContext, true, true)
        val encoder = object : VideoEncoderFactory {
            override fun createEncoder(info: VideoCodecInfo): VideoEncoder? {
                return if (info.name.uppercase() in preferredNames) baseEncoder.createEncoder(info) else null
            }

            override fun getSupportedCodecs(): Array<VideoCodecInfo> {
                val supported = baseEncoder.supportedCodecs.filter { it.name.uppercase() in preferredNames }
                return supported.sortedBy { codecPreference.indexOfFirst { pref -> pref.sdpName.equals(it.name, ignoreCase = true) }.let { idx -> if (idx >= 0) idx else Int.MAX_VALUE } }.toTypedArray()
            }
        }
        val decoder = DefaultVideoDecoderFactory(eglBase.eglBaseContext)
        factory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(encoder)
            .setVideoDecoderFactory(decoder)
            .createPeerConnectionFactory()
    }

    fun start(
        url: String,
        decision: StreamingDecision,
        onLog: (String) -> Unit,
        onError: (String) -> Unit,
        onConnected: (() -> Unit)? = null,
        onDisconnected: (() -> Unit)? = null,
    ) {
        if (!ensurePermissions(decision, onError)) return

        fun uiLog(msg: String) = activity.runOnUiThread { onLog(msg) }
        fun uiError(msg: String) = activity.runOnUiThread { onError(msg) }
        val f = factory ?: return
        try {
            val surfaceHelper = SurfaceTextureHelper.create("CaptureThread", eglBase.eglBaseContext)
            videoCapturer = createCameraCapturer()
            videoSource = f.createVideoSource(false)
            videoCapturer?.initialize(surfaceHelper, activity, videoSource!!.capturerObserver)

            fun tryStartCapture(w: Int, h: Int, fps: Int): Boolean {
                return try {
                    videoCapturer?.startCapture(w, h, fps); true
                } catch (_: Exception) {
                    false
                }
            }

            val orderedResolutions = buildList {
                add(decision.resolution)
                add(Resolution.HD_720)
                add(Resolution.HD_540)
            }.distinct()
            var captureStarted = false
            orderedResolutions.forEach { res ->
                if (!captureStarted) {
                    captureStarted = tryStartCapture(res.width, res.height, res.fps)
                }
            }
            if (!captureStarted) {
                tryStartCapture(640, 360, 30)
            }
            videoTrack = f.createVideoTrack("video0", videoSource)

            audioSource = f.createAudioSource(MediaConstraints())
            audioTrack = f.createAudioTrack("audio0", audioSource)

            val iceServers = listOf(PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer())
            val rtcConfig = PeerConnection.RTCConfiguration(iceServers).apply {
                sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN
            }
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

            try {
                val vSender = vTrans.sender
                val vParams = vSender.parameters
                vParams.encodings?.forEach { enc ->
                    enc.maxBitrateBps = decision.bitrateRange.last
                    enc.minBitrateBps = decision.bitrateRange.first
                    enc.maxFramerate = decision.resolution.fps
                    enc.scaleResolutionDownBy = 1.0
                }
                vSender.parameters = vParams
            } catch (_: Exception) {
                // Some devices may not expose parameter mutation; ignore.
            }

            val constraints = MediaConstraints().apply {
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "false"))
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "false"))
            }

            pc!!.createOffer(object : SdpObserver {
                override fun onCreateSuccess(desc: SessionDescription) {
                    val munged = SessionDescription(desc.type, preferCodecs(desc.description, decision.codecPreference))
                    pc!!.setLocalDescription(object : SdpObserver {
                        override fun onSetSuccess() {
                            waitForIceGatheringComplete {
                                Thread {
                                    try {
                                        val publishUrl = WhipUrlUtils.normalize(url)
                                        uiLog("WHIP POST: ${publishUrl}")
                                        val offer = SessionDescription(SessionDescription.Type.OFFER, munged.description)

                                        fun doPost(target: String): Pair<Int, String?> {
                                            val body = offer.description.toRequestBody("application/sdp".toMediaType())
                                            val request = Request.Builder()
                                                .url(target)
                                                .header("Content-Type", "application/sdp")
                                                .post(body)
                                                .build()
                                            http.newCall(request).execute().use { resp ->
                                                val location = resp.header("Location")
                                                if (!location.isNullOrBlank()) {
                                                    resourceUrl = location
                                                }
                                                val text = resp.body?.string()
                                                return resp.code to text
                                            }
                                        }

                                        var finalUrl = publishUrl
                                        val (code, answer) = doPost(finalUrl)
                                        if (code !in 200..299) {
                                            if (code == 404 && finalUrl.endsWith('/')) {
                                                finalUrl = finalUrl.dropLast(1)
                                                uiLog("WHIP retry (no trailing /): $finalUrl")
                                                val (retryCode, retryAnswer) = doPost(finalUrl)
                                                if (retryCode !in 200..299) {
                                                    uiError("WHIP POST failed: ${retryCode}")
                                                    return@Thread
                                                }
                                                setRemoteAnswer(retryAnswer ?: "", onConnected, onDisconnected, ::uiError)
                                            } else {
                                                uiError("WHIP POST failed: ${code}")
                                            }
                                        } else {
                                            setRemoteAnswer(answer ?: "", onConnected, onDisconnected, ::uiError)
                                        }
                                    } catch (e: Exception) {
                                        uiError("WHIP signaling error: ${e::class.java.simpleName}: ${e.message}")
                                        onDisconnected?.invoke()
                                    }
                                }.start()
                            }
                        }

                        override fun onSetFailure(error: String?) {
                            uiError("setLocalDescription: $error")
                        }

                        override fun onCreateSuccess(p0: SessionDescription?) {}
                        override fun onCreateFailure(p0: String?) {}
                    }, munged)
                }

                override fun onCreateFailure(error: String?) {
                    uiError("createOffer: $error")
                }

                override fun onSetSuccess() {}
                override fun onSetFailure(p0: String?) {}
            }, constraints)
        } catch (e: Exception) {
            onDisconnected?.invoke()
            val message = "start error: ${e::class.java.simpleName}: ${e.message}"
            activity.runOnUiThread { onError(message) }
        }
    }

    private fun setRemoteAnswer(
        answer: String,
        onConnected: (() -> Unit)?,
        onDisconnected: (() -> Unit)?,
        onError: (String) -> Unit,
    ) {
        pc?.setRemoteDescription(object : SdpObserver {
            override fun onSetSuccess() {
                activity.runOnUiThread { onConnected?.invoke() }
            }

            override fun onSetFailure(error: String?) {
                onError("setRemoteDescription: $error")
                activity.runOnUiThread { onDisconnected?.invoke() }
            }

            override fun onCreateSuccess(desc: SessionDescription?) {}
            override fun onCreateFailure(error: String?) {}
        }, SessionDescription(SessionDescription.Type.ANSWER, answer))
    }

    fun stop(onLog: (String) -> Unit) {
        try {
            resourceUrl?.let { res ->
                try {
                    http.newCall(Request.Builder().url(res).delete().build()).execute().close()
                } catch (_: Exception) {
                }
            }
            pc?.close(); pc = null
            try { videoCapturer?.stopCapture() } catch (_: Exception) {}
            videoCapturer?.dispose(); videoCapturer = null
            videoSource?.dispose(); videoSource = null
            audioSource?.dispose(); audioSource = null
            videoTrack = null
            audioTrack = null
            activity.runOnUiThread { onLog("WHIP disconnected") }
        } catch (_: Exception) {
        }
    }

    private fun waitForIceGatheringComplete(then: () -> Unit) {
        val connection = pc ?: return
        var elapsed = 0L
        fun check() {
            if (connection.iceGatheringState() == PeerConnection.IceGatheringState.COMPLETE) {
                then()
            } else {
                activity.window.decorView.postDelayed({
                    elapsed += 100
                    if (elapsed >= 2000) {
                        then()
                    } else {
                        check()
                    }
                }, 100)
            }
        }
        check()
    }

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

    private fun createCameraCapturer(): VideoCapturer? {
        val enumerator = Camera2Enumerator(activity)
        val deviceNames = enumerator.deviceNames
        deviceNames.firstOrNull { enumerator.isBackFacing(it) }?.let { return enumerator.createCapturer(it, null) }
        return deviceNames.firstOrNull()?.let { enumerator.createCapturer(it, null) }
    }

    private fun preferCodecs(original: String, preference: List<StreamCodec>): String {
        val lines = original.split("\r\n", "\n").toMutableList()
        val ptToCodec = mutableMapOf<String, String>()
        lines.forEach { line ->
            val match = SDP_CODEC_REGEX.find(line)
            if (match != null) {
                ptToCodec[match.groupValues[1]] = match.groupValues[2].uppercase()
            }
        }
        val preferenceOrder = preference.mapIndexed { index, codec -> codec.sdpName.uppercase() to index }.toMap()
        val out = mutableListOf<String>()
        for (line in lines) {
            when {
                line.startsWith("m=video ") -> {
                    val parts = line.split(" ")
                    if (parts.size > 3) {
                        val header = parts.subList(0, 3)
                        val pts = parts.drop(3)
                        val sorted = pts.withIndex().sortedWith(
                            compareBy(
                                { preferenceOrder[ptToCodec[it.value] ?: ""] ?: Int.MAX_VALUE },
                                { it.index }
                            )
                        ).map { it.value }
                        out.add((header + sorted).joinToString(" "))
                    } else {
                        out.add(line)
                    }
                }
                else -> out.add(line)
            }
        }
        return out.joinToString("\r\n")
    }

    companion object {
        private val SDP_CODEC_REGEX = Regex("^a=rtpmap:(\\d+) ([^/]+)/")
    }
}
