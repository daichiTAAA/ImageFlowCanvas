package com.imageflow.androidstream.app

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.imageflow.androidstream.app.ble.BlePrivacyService
import com.imageflow.androidstream.app.ble.PrivacyEvents
import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import org.webrtc.AudioSource
import org.webrtc.AudioTrack
import org.webrtc.Camera2Enumerator
import org.webrtc.DataChannel
import org.webrtc.DefaultVideoDecoderFactory
import org.webrtc.DefaultVideoEncoderFactory
import org.webrtc.EglBase
import org.webrtc.IceCandidate
import org.webrtc.MediaConstraints
import org.webrtc.MediaStream
import org.webrtc.PeerConnection
import org.webrtc.PeerConnectionFactory
import org.webrtc.RtpReceiver
import org.webrtc.RtpTransceiver
import org.webrtc.SessionDescription
import org.webrtc.SurfaceTextureHelper
import org.webrtc.VideoCapturer
import org.webrtc.VideoCodecInfo
import org.webrtc.VideoEncoder
import org.webrtc.VideoEncoderFactory
import org.webrtc.VideoSource
import org.webrtc.VideoTrack
import java.util.Locale

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { AndroidStreamScreen(this) }
    }
}

@Composable
private fun AndroidStreamScreen(activity: ComponentActivity) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()
    val controller = remember { WhipController(activity) }

    val streamPermissions = remember {
        listOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
    }
    val blePermissions = remember {
        buildList {
            add(Manifest.permission.ACCESS_FINE_LOCATION)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                add(Manifest.permission.BLUETOOTH_SCAN)
                add(Manifest.permission.BLUETOOTH_CONNECT)
            }
        }
    }
    val requestPermissions = remember { (streamPermissions + blePermissions).distinct() }

    var permissionState by remember { mutableStateOf<Map<String, Boolean>>(emptyMap()) }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        permissionState = permissionState.toMutableMap().apply { putAll(result) }
    }

    LaunchedEffect(Unit) {
        val initial = requestPermissions.associateWith {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
        permissionState = initial
    }

    val hasStreamPermissions = streamPermissions.all { permissionState[it] == true }
    val hasBlePermissions = blePermissions.isEmpty() || blePermissions.all { permissionState[it] == true }

    var whipUrlInput by rememberSaveable { mutableStateOf("") }
    var autoStart by rememberSaveable { mutableStateOf(true) }
    var autoResume by rememberSaveable { mutableStateOf(true) }

    var beaconType by rememberSaveable { mutableStateOf("any") }
    var edNamespace by rememberSaveable { mutableStateOf("") }
    var edInstance by rememberSaveable { mutableStateOf("") }
    var ibUuid by rememberSaveable { mutableStateOf("") }
    var ibMajor by rememberSaveable { mutableStateOf("") }
    var ibMinor by rememberSaveable { mutableStateOf("") }
    var enterRssi by rememberSaveable { mutableStateOf("-70") }
    var exitRssi by rememberSaveable { mutableStateOf("-80") }
    var enterSec by rememberSaveable { mutableStateOf("2") }
    var exitSec by rememberSaveable { mutableStateOf("5") }
    var holdSec by rememberSaveable { mutableStateOf("30") }
    var matchStrict by rememberSaveable { mutableStateOf(true) }
    var holdExtendNonUid by rememberSaveable { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        whipUrlInput = AppConfig.getWhipUrl(context)
        autoStart = AppConfig.getAutoStart(context)
        autoResume = AppConfig.getAutoResume(context)
        beaconType = AppConfig.getBeaconType(context)
        edNamespace = AppConfig.getEddystoneNamespace(context)
        edInstance = AppConfig.getEddystoneInstance(context)
        ibUuid = AppConfig.getIBeaconUuid(context) ?: ""
        ibMajor = AppConfig.getIBeaconMajor(context)?.toString() ?: ""
        ibMinor = AppConfig.getIBeaconMinor(context)?.toString() ?: ""
        enterRssi = AppConfig.getEnterRssi(context).toString()
        exitRssi = AppConfig.getExitRssi(context).toString()
        enterSec = AppConfig.getEnterSeconds(context).toString()
        exitSec = AppConfig.getExitSeconds(context).toString()
        holdSec = AppConfig.getPresenceHoldSeconds(context).toString()
        matchStrict = AppConfig.isMatchStrict(context)
        holdExtendNonUid = AppConfig.getHoldExtendNonUid(context)
    }

    var logText by remember { mutableStateOf("待機中") }
    var streaming by remember { mutableStateOf(false) }
    var privacyActive by remember { mutableStateOf(false) }
    var bleRssi by remember { mutableStateOf<Int?>(null) }
    var bleProximity by remember { mutableStateOf("far") }
    val detectedBeacons = remember { mutableStateMapOf<String, BeaconInfo>() }

    var testUrl by remember { mutableStateOf("") }
    var testResult by remember { mutableStateOf("") }

    fun startStreaming(desiredUrl: String? = null) {
        val target = (desiredUrl ?: whipUrlInput).trim()
        if (target.isBlank()) {
            logText = "WHIP URL を入力してください"
            return
        }
        val sanitized = AppConfig.sanitizeWhipUrl(context, target)
        AppConfig.setWhipUrl(context, sanitized)
        whipUrlInput = sanitized
        controller.start(
            url = sanitized,
            onLog = { logText = it },
            onError = { logText = it },
            onConnected = {
                streaming = true
                logText = "配信を開始しました"
            },
            onDisconnected = {
                val wasStreaming = streaming
                streaming = false
                if (wasStreaming) {
                    logText = "配信を停止しました"
                }
            }
        )
    }

    fun stopStreaming() {
        controller.stop { msg -> logText = msg }
        streaming = false
    }

    LaunchedEffect(hasBlePermissions) {
        if (hasBlePermissions) {
            try {
                BlePrivacyService.start(context)
            } catch (e: Exception) {
                logText = "BLEスキャン開始エラー: ${e.message}"
            }
        }
    }

    LaunchedEffect(hasStreamPermissions, autoStart, privacyActive) {
        if (hasStreamPermissions && autoStart && !streaming && !privacyActive) {
            startStreaming(AppConfig.getWhipUrl(context))
        }
    }

    fun updateDetectedBeacons(idRaw: String?, rssi: Int?, proximity: String) {
        val id = idRaw?.takeIf { it.isNotBlank() } ?: return
        val ts = System.currentTimeMillis()
        detectedBeacons[id] = BeaconInfo(rssi, proximity, ts)
        val cutoff = ts - 15_000
        val stale = detectedBeacons.entries.toList().filter { it.value.lastSeen < cutoff }
        stale.forEach { entry -> detectedBeacons.remove(entry.key) }
    }

    DisposableEffect(Unit) {
        val filter = IntentFilter().apply {
            addAction(PrivacyEvents.ACTION_PRIVACY_ENTER)
            addAction(PrivacyEvents.ACTION_PRIVACY_EXIT)
            addAction(PrivacyEvents.ACTION_PRIVACY_UPDATE)
        }
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context?, intent: Intent?) {
                when (intent?.action) {
                    PrivacyEvents.ACTION_PRIVACY_ENTER -> {
                        privacyActive = true
                        val beacon = intent.getStringExtra(PrivacyEvents.EXTRA_BEACON_ID)
                        val rssiVal = if (intent.hasExtra(PrivacyEvents.EXTRA_RSSI)) intent.getIntExtra(PrivacyEvents.EXTRA_RSSI, -127) else null
                        bleRssi = rssiVal
                        bleProximity = "near"
                        updateDetectedBeacons(beacon, rssiVal, "near")
                        if (streaming) {
                            stopStreaming()
                            logText = "プライバシーゾーン検知: 配信を停止しました"
                        } else {
                            logText = "プライバシーゾーン検知"
                        }
                    }
                    PrivacyEvents.ACTION_PRIVACY_EXIT -> {
                        privacyActive = false
                        val beacon = intent.getStringExtra(PrivacyEvents.EXTRA_BEACON_ID)
                        val rssiVal = if (intent.hasExtra(PrivacyEvents.EXTRA_RSSI)) intent.getIntExtra(PrivacyEvents.EXTRA_RSSI, -127) else null
                        bleRssi = rssiVal
                        bleProximity = "far"
                        updateDetectedBeacons(beacon, rssiVal, "far")
                        val shouldAutoResume = AppConfig.getAutoResume(context)
                        val urlNow = AppConfig.getWhipUrl(context)
                        val permsOk = streamPermissions.all {
                            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
                        }
                        if (shouldAutoResume && permsOk && !privacyActive) {
                            autoResume = true
                            startStreaming(urlNow)
                            logText = "プライバシーゾーン解除: 配信を再開します"
                        } else {
                            autoResume = shouldAutoResume
                            logText = "プライバシーゾーン解除"
                        }
                    }
                    PrivacyEvents.ACTION_PRIVACY_UPDATE -> {
                        val beacon = intent.getStringExtra(PrivacyEvents.EXTRA_BEACON_ID)
                        val updatedRssi = if (intent.hasExtra(PrivacyEvents.EXTRA_RSSI)) intent.getIntExtra(PrivacyEvents.EXTRA_RSSI, -127) else bleRssi
                        val updatedProx = intent.getStringExtra(PrivacyEvents.EXTRA_PROXIMITY) ?: bleProximity
                        bleRssi = updatedRssi
                        bleProximity = updatedProx
                        updateDetectedBeacons(beacon, updatedRssi, updatedProx)
                        privacyActive = intent.getBooleanExtra(PrivacyEvents.EXTRA_IN_PRIVACY, privacyActive)
                    }
                }
            }
        }
        context.registerReceiver(receiver, filter)
        onDispose { context.unregisterReceiver(receiver) }
    }

    MaterialTheme {
        Surface(Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(scrollState)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "Android Stream Controller",
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
                )

                if (!hasStreamPermissions) {
                    Text(
                        "カメラ・マイクの権限を付与してください",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error
                    )
                } else {
                    Text("配信に必要な権限は許可済みです", style = MaterialTheme.typography.bodyMedium)
                }
                if (!hasBlePermissions) {
                    Text(
                        "BLEプライバシー制御の権限が未許可です (位置情報/Bluetooth)",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.tertiary
                    )
                }
                TextButton(onClick = { permissionLauncher.launch(requestPermissions.toTypedArray()) }) {
                    Text("権限をリクエスト")
                }

                HorizontalDivider()

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("WHIP 配信設定", style = MaterialTheme.typography.titleMedium)
                    OutlinedTextField(
                        modifier = Modifier.fillMaxWidth(),
                        value = whipUrlInput,
                        onValueChange = { whipUrlInput = it },
                        label = { Text("WHIP URL") },
                        singleLine = true
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Button(
                            onClick = {
                                AppConfig.setWhipUrl(context, whipUrlInput.trim())
                                logText = "配信先URLを保存しました"
                            }
                        ) { Text("URLを保存") }
                        OutlinedButton(onClick = { startStreaming() }, enabled = hasStreamPermissions && !streaming) {
                            Text("配信開始")
                        }
                        OutlinedButton(onClick = { stopStreaming() }, enabled = streaming) {
                            Text("配信停止")
                        }
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Switch(checked = autoStart, onCheckedChange = {
                            autoStart = it
                            AppConfig.setAutoStart(context, it)
                        })
                        Spacer(Modifier.width(8.dp))
                        Text("アプリ起動時に自動開始")
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Switch(checked = autoResume, onCheckedChange = {
                            autoResume = it
                            AppConfig.setAutoResume(context, it)
                        })
                        Spacer(Modifier.width(8.dp))
                        Text("プライバシー解除時に再開")
                    }
                }

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("現在の状態", style = MaterialTheme.typography.titleMedium)
                    Text("ログ: $logText", maxLines = 3, overflow = TextOverflow.Ellipsis)
                    Text(if (streaming) "配信中" else "停止中")
                }

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("BLE プライバシー設定", style = MaterialTheme.typography.titleMedium)
                    Text("検出タイプ", style = MaterialTheme.typography.labelLarge)
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        val options = listOf(
                            "any" to "任意",
                            "eddystone_uid" to "Eddystone UID",
                            "ibeacon" to "iBeacon"
                        )
                        options.forEach { (value, label) ->
                            FilterChip(
                                selected = beaconType == value,
                                onClick = {
                                    beaconType = value
                                    AppConfig.setBeaconType(context, value)
                                    logText = "ビーコンタイプを $label に設定"
                                },
                                label = { Text(label) }
                            )
                        }
                    }
                    OutlinedTextField(
                        modifier = Modifier.fillMaxWidth(),
                        value = edNamespace,
                        onValueChange = { edNamespace = it.lowercase(Locale.ROOT) },
                        label = { Text("Eddystone Namespace (hex)") },
                        singleLine = true
                    )
                    OutlinedTextField(
                        modifier = Modifier.fillMaxWidth(),
                        value = edInstance,
                        onValueChange = { edInstance = it.lowercase(Locale.ROOT) },
                        label = { Text("Eddystone Instance (hex)") },
                        singleLine = true
                    )
                    OutlinedTextField(
                        modifier = Modifier.fillMaxWidth(),
                        value = ibUuid,
                        onValueChange = { ibUuid = it.lowercase(Locale.ROOT) },
                        label = { Text("iBeacon UUID") },
                        singleLine = true
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(
                            modifier = Modifier.weight(1f),
                            value = ibMajor,
                            onValueChange = { ibMajor = it.filter { ch -> ch.isDigit() } },
                            label = { Text("iBeacon Major") },
                            singleLine = true
                        )
                        OutlinedTextField(
                            modifier = Modifier.weight(1f),
                            value = ibMinor,
                            onValueChange = { ibMinor = it.filter { ch -> ch.isDigit() } },
                            label = { Text("iBeacon Minor") },
                            singleLine = true
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(
                            modifier = Modifier.weight(1f),
                            value = enterRssi,
                            onValueChange = { enterRssi = it.filter { ch -> ch == '-' || ch.isDigit() } },
                            label = { Text("入域RSSI") },
                            singleLine = true
                        )
                        OutlinedTextField(
                            modifier = Modifier.weight(1f),
                            value = exitRssi,
                            onValueChange = { exitRssi = it.filter { ch -> ch == '-' || ch.isDigit() } },
                            label = { Text("離域RSSI") },
                            singleLine = true
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(
                            modifier = Modifier.weight(1f),
                            value = enterSec,
                            onValueChange = { enterSec = it.filter { ch -> ch.isDigit() } },
                            label = { Text("入域判定秒数") },
                            singleLine = true
                        )
                        OutlinedTextField(
                            modifier = Modifier.weight(1f),
                            value = exitSec,
                            onValueChange = { exitSec = it.filter { ch -> ch.isDigit() } },
                            label = { Text("離域判定秒数") },
                            singleLine = true
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(
                            modifier = Modifier.weight(1f),
                            value = holdSec,
                            onValueChange = { holdSec = it.filter { ch -> ch.isDigit() } },
                            label = { Text("ビーコン保持秒数") },
                            singleLine = true
                        )
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Switch(checked = matchStrict, onCheckedChange = {
                            matchStrict = it
                            AppConfig.setMatchStrict(context, it)
                        })
                        Spacer(Modifier.width(8.dp))
                        Text("許可されたビーコンのみで制御")
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Switch(checked = holdExtendNonUid, onCheckedChange = {
                            holdExtendNonUid = it
                            AppConfig.setHoldExtendNonUid(context, it)
                        })
                        Spacer(Modifier.width(8.dp))
                        Text("Eddystoneの非UIDフレームで保持延長")
                    }
                    Button(onClick = {
                        AppConfig.setEddystoneUid(context, edNamespace.ifBlank { null }, edInstance.ifBlank { null })
                        val majorValue = ibMajor.toIntOrNull()
                        val minorValue = ibMinor.toIntOrNull()
                        AppConfig.setIBeacon(context, ibUuid.ifBlank { null }, majorValue, minorValue)
                        enterRssi.toIntOrNull()?.let { AppConfig.setEnterRssi(context, it) }
                        exitRssi.toIntOrNull()?.let { AppConfig.setExitRssi(context, it) }
                        enterSec.toIntOrNull()?.let { AppConfig.setEnterSeconds(context, it) }
                        exitSec.toIntOrNull()?.let { AppConfig.setExitSeconds(context, it) }
                        holdSec.toIntOrNull()?.let { AppConfig.setPresenceHoldSeconds(context, it) }
                        logText = "BLE設定を保存しました"
                        try {
                            BlePrivacyService.start(context)
                        } catch (e: Exception) {
                            logText = "BLEサービス再起動に失敗: ${e.message}"
                        }
                    }) {
                        Text("BLE設定を保存")
                    }
                    Text(
                        "BLE状態: RSSI=${bleRssi?.let { "$it dBm" } ?: "-"}  距離=${proximityLabel(bleProximity)}",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    if (detectedBeacons.isEmpty()) {
                        Text("検出ビーコン: なし", style = MaterialTheme.typography.bodySmall)
                    } else {
                        Text("検出ビーコン一覧", style = MaterialTheme.typography.labelLarge)
                        val nowMs = System.currentTimeMillis()
                        detectedBeacons.entries
                            .sortedByDescending { it.value.lastSeen }
                            .forEach { entry ->
                                val info = entry.value
                                val ageSec = ((nowMs - info.lastSeen) / 1000).coerceAtLeast(0)
                                val rssiLabel = info.rssi?.let { "$it dBm" } ?: "-"
                                Text(
                                    "・${entry.key}  RSSI=$rssiLabel  距離=${proximityLabel(info.proximity)}  (${ageSec}s 前)",
                                    style = MaterialTheme.typography.bodySmall
                                )
                            }
                    }
                    Text(if (privacyActive) "プライバシーモード中" else "プライバシーモード外", style = MaterialTheme.typography.bodyMedium)
                }

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("接続テスト", style = MaterialTheme.typography.titleMedium)
                    Button(onClick = {
                        val origin = extractOrigin(whipUrlInput) ?: whipUrlInput
                        val url = origin.trimEnd('/') + "/whip/test/"
                        testUrl = url
                        testResult = ""
                        controller.testWhipEndpoint(url) { result -> testResult = result }
                    }) {
                        Text("WHIP エンドポイントをテスト")
                    }
                    if (testUrl.isNotBlank()) Text("URL: $testUrl", style = MaterialTheme.typography.bodySmall)
                    if (testResult.isNotBlank()) Text("結果: $testResult", style = MaterialTheme.typography.bodySmall)
                }

                Spacer(Modifier.height(24.dp))
            }
        }
    }
}

private data class BeaconInfo(val rssi: Int?, val proximity: String, val lastSeen: Long)

private fun proximityLabel(proximity: String): String = when (proximity) {
    "near" -> "近"
    "mid" -> "中"
    "far" -> "遠"
    else -> proximity
}

private fun normalizeWhipPostUrl(raw: String): String {
    val parsed = raw.toHttpUrlOrNull()
    if (parsed != null) {
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
    var s = raw.trim()
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

private class WhipController(private val activity: ComponentActivity) {
    private val logTag = "WhipController"
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
            .setEnableInternalTracer(false)
            .createInitializationOptions()
        PeerConnectionFactory.initialize(initOptions)
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

    private fun preferH264(original: String): String {
        val lines = original.split("\r\n", "\n").toMutableList()
        var h264Pt: String? = null
        val keepPts = mutableSetOf<String>()
        lines.forEach { line ->
            val m = Regex("^a=rtpmap:(\\d+) H264/90000").find(line)
            if (m != null) {
                h264Pt = m.groupValues[1]
                keepPts.add(h264Pt!!)
            }
        }
        if (h264Pt == null) return original
        lines.forEach { line ->
            val m = Regex("^a=fmtp:(\\d+) apt=${h264Pt}").find(line)
            if (m != null) keepPts.add(m.groupValues[1])
        }
        val out = mutableListOf<String>()
        for (line in lines) {
            when {
                line.startsWith("m=video ") -> {
                    val parts = line.split(" ").toMutableList()
                    if (parts.size > 3) {
                        val header = parts.subList(0, 3).joinToString(" ")
                        val pts = parts.drop(3).filter { keepPts.contains(it) }
                        out.add((listOf(header) + pts).joinToString(" "))
                    } else {
                        out.add(line)
                    }
                }
                line.startsWith("a=rtpmap:") || line.startsWith("a=fmtp:") || line.startsWith("a=rtcp-fb:") -> {
                    val m = Regex("^a=(?:rtpmap|fmtp|rtcp-fb):(\\d+)").find(line)
                    val pt = m?.groupValues?.getOrNull(1)
                    if (pt == null || keepPts.contains(pt)) {
                        out.add(line)
                    }
                }
                else -> out.add(line)
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
            fun tryStartCapture(w: Int, h: Int, fps: Int): Boolean {
                return try {
                    videoCapturer?.startCapture(w, h, fps)
                    true
                } catch (_: Exception) {
                    false
                }
            }
            if (!(tryStartCapture(1920, 1080, 30) || tryStartCapture(1280, 720, 30) || tryStartCapture(960, 540, 30))) {
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
                override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>) {}
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
                    enc.maxBitrateBps = 6_000_000
                    enc.minBitrateBps = 800_000
                    enc.maxFramerate = 30
                    enc.scaleResolutionDownBy = 1.0
                }
                vSender.parameters = vParams
            } catch (_: Exception) {
            }

            val constraints = MediaConstraints().apply {
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "false"))
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "false"))
            }
            pc!!.createOffer(object : org.webrtc.SdpObserver {
                override fun onCreateSuccess(desc: SessionDescription) {
                    val munged = SessionDescription(desc.type, preferH264(desc.description))
                    pc!!.setLocalDescription(object : org.webrtc.SdpObserver {
                        override fun onSetSuccess() {
                            waitForIceGatheringComplete {
                                val offerSdp = pc!!.localDescription?.description ?: return@waitForIceGatheringComplete
                                val mediaType = "application/sdp".toMediaType()
                                val publishUrl = normalizeWhipPostUrl(url)
                                uiLog("WHIP POST: $publishUrl")
                                Thread {
                                    try {
                                        uiLog("WHIP POST: $publishUrl")
                                        fun doPost(url: String): Triple<Int, String?, String?> {
                                            val req = Request.Builder()
                                                .url(url)
                                                .addHeader("Content-Type", "application/sdp")
                                                .addHeader("Accept", "application/sdp")
                                                .post(offerSdp.toRequestBody(mediaType))
                                                .build()
                                            http.newCall(req).execute().use { resp ->
                                                val location = resp.header("Location")
                                                uiLog("WHIP 応答: ${resp.code} ${resp.message}")
                                                location?.let { Log.i(logTag, "WHIP Location: $it") }
                                                val loc = resp.header("Location")
                                                if (resp.code in listOf(301, 302, 307, 308) && loc != null) {
                                                    val base = url.toHttpUrlOrNull()
                                                    val next = if (base != null) base.resolve(loc)?.toString() else loc
                                                    if (next != null) {
                                                        uiLog("WHIP redirect -> $next")
                                                        return doPost(next)
                                                    }
                                                }
                                                val body = if (resp.isSuccessful) (resp.body?.string() ?: "") else null
                                                return Triple(resp.code, body, location)
                                            }
                                        }

                                        var finalUrl = publishUrl
                                        var code: Int
                                        var answer: String? = null
                                        var locationHeader: String? = null
                                        try {
                                            val (c, a, loc) = doPost(finalUrl)
                                            code = c
                                            answer = a
                                            locationHeader = loc
                                        } catch (e: Exception) {
                                            throw e
                                        }

                                        if (code == 404 && finalUrl.endsWith('/')) {
                                            finalUrl = finalUrl.dropLast(1)
                                            uiLog("WHIP retry: $finalUrl")
                                            val (c2, a2, loc2) = doPost(finalUrl)
                                            code = c2
                                            answer = a2
                                            locationHeader = loc2
                                        }

                                        if (code !in 200..299) {
                                            uiError("WHIP POST failed: $code")
                                            onDisconnected?.invoke()
                                            return@Thread
                                        }

                                        resourceUrl = locationHeader ?: finalUrl
                                        locationHeader?.let { uiLog("WHIP Location: $it") }
                                        pc!!.setRemoteDescription(object : org.webrtc.SdpObserver {
                                            override fun onSetSuccess() {
                                                uiLog("WHIP connected")
                                                onConnected?.invoke()
                                            }
                                            override fun onSetFailure(error: String?) { uiError("setRemoteDescription: $error") }
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
                        override fun onSetFailure(error: String?) { uiError("setLocalDescription: $error") }
                        override fun onCreateSuccess(p0: SessionDescription?) {}
                        override fun onCreateFailure(p0: String?) {}
                    }, munged)
                }
                override fun onCreateFailure(error: String?) { uiError("createOffer: $error") }
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
                try {
                    http.newCall(Request.Builder().url(res).delete().build()).execute().close()
                } catch (_: Exception) {}
            }
            pc?.close()
            pc = null
            try { videoCapturer?.stopCapture() } catch (_: Exception) {}
            videoCapturer?.dispose(); videoCapturer = null
            videoSource?.dispose(); videoSource = null
            audioSource?.dispose(); audioSource = null
            videoTrack = null
            audioTrack = null
            onLog("WHIP disconnected")
        } catch (_: Exception) {}
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
}
