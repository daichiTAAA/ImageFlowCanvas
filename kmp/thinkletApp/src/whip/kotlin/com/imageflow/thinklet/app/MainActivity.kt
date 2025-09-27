package com.imageflow.thinklet.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.imageflow.thinklet.app.audio.AudioService
import com.imageflow.thinklet.app.command.BackendApiClient
import com.imageflow.thinklet.app.command.VoiceCommandProcessor
import com.imageflow.thinklet.app.command.WorkCommandProcessor
import com.imageflow.thinklet.app.command.WorkState
import com.imageflow.thinklet.app.streaming.StreamOptimizer
import com.imageflow.thinklet.app.streaming.StreamingDecision
import com.imageflow.thinklet.app.streaming.WhipController
import com.imageflow.thinklet.app.streaming.WhipUrlUtils
import java.util.UUID

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { ThinkletAppScreen(this) }
    }
}

@Composable
private fun ThinkletAppScreen(activity: ComponentActivity) {
    val context = LocalContext.current
    val logMessages = remember { mutableStateListOf("Ready.") }

    var hasPermissions by remember { mutableStateOf(false) }
    var isStreaming by remember { mutableStateOf(false) }
    var workState by remember { mutableStateOf(WorkState.IDLE) }
    var sessionId by remember { mutableStateOf<String?>(null) }
    var audioStatus by remember { mutableStateOf("音声認識を待機中") }
    var lastCommandText by remember { mutableStateOf<String?>(null) }
    var lastCommandConfidence by remember { mutableStateOf<Float?>(null) }
    var testUrl by remember { mutableStateOf("") }
    var testResult by remember { mutableStateOf("") }

    val backendClient = remember { BackendApiClient(context) }
    val voiceProcessor = remember {
        VoiceCommandProcessor(
            deviceNameProvider = { AppConfig.getDeviceName(context) },
            confidenceProvider = { AppConfig.getVoiceConfidenceThreshold(context) }
        )
    }
    val workProcessor = remember {
        WorkCommandProcessor(
            context = context,
            backend = backendClient,
            onLog = { message -> logMessages.addWithLimit(message) },
            onStateChanged = { state -> workState = state },
            onSessionChanged = { id: UUID? -> sessionId = id?.toString() },
            onExitRequested = { activity.finish() }
        )
    }
    val streamOptimizer = remember { StreamOptimizer() }
    val whipController = remember { WhipController(activity) }

    val audioService = remember {
        AudioService(
            context = context,
            onPhrase = { phrase ->
                val command = voiceProcessor.evaluate(phrase)
                if (command != null) {
                    lastCommandText = command.rawText
                    lastCommandConfidence = command.confidence
                    workProcessor.process(command)
                }
            },
            onStatus = { status ->
                audioStatus = status
                logMessages.addWithLimit(status)
            },
            onError = { error ->
                audioStatus = error
                logMessages.addWithLimit("[Audio] $error")
            }
        )
    }

    val configuredWhipUrl = remember { AppConfig.getWhipUrl(context) }
    val autoStart = remember { AppConfig.getAutoStart(context) }
    val deviceName = remember { AppConfig.getDeviceName(context) }

    LaunchedEffect(Unit) {
        val required = listOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
        hasPermissions = required.all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
        if (!hasPermissions) {
            logMessages.addWithLimit("権限が不足しています (adbで事前に付与してください)")
        }
    }

    LaunchedEffect(hasPermissions) {
        if (hasPermissions) {
            audioService.start()
        }
    }

    LaunchedEffect(isStreaming) {
        workProcessor.updateStreamingState(isStreaming)
    }

    LaunchedEffect(hasPermissions, autoStart, configuredWhipUrl) {
        if (autoStart && hasPermissions && configuredWhipUrl.isNotBlank()) {
            val decision = streamOptimizer.decide(
                batteryLevel = null,
                networkQuality = null,
                workState = workState,
            )
            isStreaming = true
            whipController.start(
                configuredWhipUrl,
                decision,
                onLog = { logMessages.addWithLimit(it) },
                onError = {
                    logMessages.addWithLimit("[WHIP] $it")
                    isStreaming = false
                    workProcessor.updateStreamingState(false)
                },
                onConnected = {
                    isStreaming = true
                    workProcessor.updateStreamingState(true)
                },
                onDisconnected = {
                    isStreaming = false
                    workProcessor.updateStreamingState(false)
                }
            )
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            whipController.stop { }
            audioService.release()
            workProcessor.dispose()
        }
    }

    MaterialTheme {
        Surface(Modifier.fillMaxSize()) {
            ThinkletDashboard(
                deviceName = deviceName,
                backendUrl = AppConfig.getBackendUrl(context),
                whipUrl = configuredWhipUrl,
                workState = workState,
                sessionId = sessionId,
                isStreaming = isStreaming,
                audioStatus = audioStatus,
                lastCommand = lastCommandText,
                lastConfidence = lastCommandConfidence,
                logs = logMessages,
                postUrl = WhipUrlUtils.normalize(configuredWhipUrl),
                testUrl = testUrl,
                testResult = testResult,
                onStartStreaming = {
                    if (!hasPermissions) {
                        logMessages.addWithLimit("権限が不足しています")
                        return@ThinkletDashboard
                    }
                    val decision = streamOptimizer.decide(
                        batteryLevel = null,
                        networkQuality = null,
                        workState = workState,
                    )
                    isStreaming = true
                    whipController.start(
                        configuredWhipUrl,
                        decision,
                        onLog = { logMessages.addWithLimit(it) },
                        onError = {
                            logMessages.addWithLimit("[WHIP] $it")
                            isStreaming = false
                            workProcessor.updateStreamingState(false)
                        },
                        onConnected = {
                            isStreaming = true
                            workProcessor.updateStreamingState(true)
                        },
                        onDisconnected = {
                            isStreaming = false
                            workProcessor.updateStreamingState(false)
                        }
                    )
                },
                onStopStreaming = {
                    whipController.stop { message -> logMessages.addWithLimit(message) }
                    isStreaming = false
                    workProcessor.updateStreamingState(false)
                },
                onTestConnection = {
                    val origin = WhipUrlUtils.extractOrigin(configuredWhipUrl) ?: configuredWhipUrl
                    val urlToTest = origin.trimEnd('/') + "/whip/test/"
                    testUrl = urlToTest
                    testResult = "テスト中…"
                    whipController.testWhipEndpoint(urlToTest) { result ->
                        testResult = result
                    }
                }
            )
        }
    }
}

@Composable
private fun ThinkletDashboard(
    deviceName: String,
    backendUrl: String,
    whipUrl: String,
    workState: WorkState,
    sessionId: String?,
    isStreaming: Boolean,
    audioStatus: String,
    lastCommand: String?,
    lastConfidence: Float?,
    logs: List<String>,
    postUrl: String,
    testUrl: String,
    testResult: String,
    onStartStreaming: () -> Unit,
    onStopStreaming: () -> Unit,
    onTestConnection: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.02f))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(text = "THINKLET 映像配信", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text(text = "デバイス名: $deviceName", style = MaterialTheme.typography.titleMedium)
        Text(text = "Backend API: $backendUrl", style = MaterialTheme.typography.bodyMedium)
        Text(text = "WHIP URL: $whipUrl", style = MaterialTheme.typography.bodyMedium)
        Text(text = "POST先: $postUrl", style = MaterialTheme.typography.bodySmall)
        Text(text = "作業状態: ${workState.displayName}", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
        Text(text = "セッションID: ${sessionId ?: "--"}")
        Text(text = "配信状態: ${if (isStreaming) "配信中" else "停止中"}", color = if (isStreaming) Color(0xFF2E7D32) else Color(0xFFB71C1C))
        Text(text = "音声状態: $audioStatus")
        if (!lastCommand.isNullOrBlank()) {
            Text(text = "最終コマンド: $lastCommand (${String.format("%.2f", lastConfidence ?: 0f)})")
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = onStartStreaming, enabled = !isStreaming) { Text("配信開始") }
            Button(onClick = onStopStreaming, enabled = isStreaming) { Text("配信停止") }
            Button(onClick = onTestConnection) { Text("接続テスト") }
        }
        if (testUrl.isNotBlank()) {
            Text(text = "テストURL: $testUrl", style = MaterialTheme.typography.bodySmall)
            Text(text = "テスト結果: $testResult", style = MaterialTheme.typography.bodySmall)
        }

        Divider()
        Text(text = "ログ", style = MaterialTheme.typography.titleMedium)
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
            reverseLayout = true
        ) {
            items(logs.reversed()) { log ->
                Text(text = log, style = MaterialTheme.typography.bodySmall)
                Spacer(modifier = Modifier.height(4.dp))
            }
        }
    }
}

private fun MutableList<String>.addWithLimit(message: String, limit: Int = 120) {
    add(0, message)
    while (size > limit) {
        removeAt(lastIndex)
    }
}
