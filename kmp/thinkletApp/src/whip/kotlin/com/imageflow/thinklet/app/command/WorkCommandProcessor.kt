package com.imageflow.thinklet.app.command

import android.content.Context
import android.provider.Settings
import com.imageflow.thinklet.app.AppConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.cancel
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.util.UUID

class WorkCommandProcessor(
    private val context: Context,
    private val backend: BackendApiClient,
    private val onLog: (String) -> Unit,
    private val onStateChanged: (WorkState) -> Unit,
    private val onSessionChanged: (UUID?) -> Unit,
    private val onExitRequested: () -> Unit = {},
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val timestampFormatter = DateTimeFormatter.ISO_INSTANT

    private var currentState: WorkState = WorkState.IDLE
    private var currentSessionId: UUID? = null
    private var isStreaming: Boolean = false
    private var lastBatteryLevel: Int? = null
    private var lastTemperatureC: Double? = null
    private var lastNetworkQuality: String? = null

    private val deviceIdentifier: String? by lazy {
        Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            ?.takeIf { it.isNotBlank() }
    }

    private fun postLog(message: String) {
        scope.launch(Dispatchers.Main) {
            onLog(message)
        }
    }

    fun dispose() {
        scope.cancel()
    }

    fun updateStreamingState(streaming: Boolean) {
        if (isStreaming == streaming) return
        isStreaming = streaming
        pushStatusAsync(reason = "streaming")
    }

    fun updateBatteryLevel(level: Int?) {
        lastBatteryLevel = level
        pushStatusAsync(reason = "battery")
    }

    fun updateTemperature(temp: Double?) {
        lastTemperatureC = temp
        pushStatusAsync(reason = "temperature")
    }

    fun updateNetworkQuality(quality: String?) {
        lastNetworkQuality = quality
        pushStatusAsync(reason = "network")
    }

    fun process(command: VoiceCommand) {
        if (command.provisional) {
            // We only act on final recognition results to avoid jitter
            return
        }
        val myName = AppConfig.getDeviceName(context)
        val targetName = command.deviceName ?: myName
        if (!targetName.equals(myName, ignoreCase = true)) {
            postLog("別デバイス宛のコマンドを無視します: ${command.deviceName}")
            return
        }
        when (command.action) {
            VoiceCommandAction.WORK_START -> handleWorkStart(command)
            VoiceCommandAction.WORK_END -> handleWorkEnd(command)
            VoiceCommandAction.BREAK_START -> transitionTo(when {
                currentState.isRecording -> WorkState.BREAK_RECORDING
                else -> WorkState.BREAK
            }, reason = "休憩開始")
            VoiceCommandAction.BREAK_END -> transitionTo(when {
                currentState.isRecording -> WorkState.WORKING_RECORDING
                else -> WorkState.WORKING
            }, reason = "休憩終了")
            VoiceCommandAction.RECORD_START -> handleRecordingStart()
            VoiceCommandAction.RECORD_STOP -> handleRecordingStop()
            VoiceCommandAction.RECORD_PAUSE -> transitionTo(WorkState.RECORDING_PAUSED, reason = "録画一時停止")
            VoiceCommandAction.RECORD_RESUME -> transitionTo(when {
                currentState == WorkState.RECORDING_PAUSED -> WorkState.RECORDING
                currentState == WorkState.BREAK_RECORDING -> WorkState.BREAK_RECORDING
                currentState == WorkState.WORKING_RECORDING -> WorkState.WORKING_RECORDING
                currentState == WorkState.WORKING -> WorkState.WORKING_RECORDING
                else -> WorkState.RECORDING
            }, reason = "録画再開")
            VoiceCommandAction.STATUS_QUERY -> logStatus()
            VoiceCommandAction.DEVICE_NAME_QUERY -> postLog("私は${myName}です")
            VoiceCommandAction.VOLUME_UP -> postLog("音量制御は未実装です。設定アプリで調整してください")
            VoiceCommandAction.VOLUME_DOWN -> postLog("音量制御は未実装です。設定アプリで調整してください")
            VoiceCommandAction.APP_EXIT -> onExitRequested()
            VoiceCommandAction.CONNECTION_CHECK -> requestSessionStatus()
        }
    }

    private fun handleWorkStart(command: VoiceCommand) {
        if (currentState == WorkState.WORKING || currentState == WorkState.WORKING_RECORDING) {
            postLog("既に作業中です")
            return
        }
        scope.launch {
            postLog("作業開始をバックエンドに通知します…")
            val payload = backend.buildStartPayload(
                deviceName = AppConfig.getDeviceName(context),
                deviceIdentifier = deviceIdentifier,
                command = command,
                sessionHint = currentSessionId,
                batteryLevel = lastBatteryLevel,
                networkQuality = lastNetworkQuality,
                temperatureC = lastTemperatureC,
            )
            val result = backend.postWorkStart(payload)
            if (result.isSuccess) {
                val response = result.getOrNull()
                val sessionId = runCatching { UUID.fromString(response?.sessionId) }.getOrNull()
                val newState = if (currentState.isRecording) WorkState.WORKING_RECORDING else WorkState.WORKING
                withContext(Dispatchers.Main) {
                    currentSessionId = sessionId
                    postLog("作業セッション開始: ${sessionId ?: "unknown"}")
                    transitionTo(newState, push = false, reason = "作業開始")
                    onSessionChanged(sessionId)
                    pushStatusAsync(reason = "session-start")
                }
            } else {
                withContext(Dispatchers.Main) {
                    postLog("作業開始の通知に失敗: ${result.exceptionOrNull()?.message}")
                }
            }
        }
    }

    private fun handleWorkEnd(command: VoiceCommand) {
        scope.launch {
            postLog("作業終了をバックエンドに通知します…")
            val payload = backend.buildEndPayload(
                sessionId = currentSessionId,
                deviceName = AppConfig.getDeviceName(context),
                command = command,
                batteryLevel = lastBatteryLevel,
                networkQuality = lastNetworkQuality,
                temperatureC = lastTemperatureC,
            )
            val result = backend.postWorkEnd(payload)
            if (result.isSuccess) {
                val nextState = when {
                    currentState.isRecording -> WorkState.RECORDING
                    else -> WorkState.IDLE
                }
                withContext(Dispatchers.Main) {
                    postLog("作業終了を記録しました")
                    currentSessionId = null
                    onSessionChanged(null)
                    transitionTo(nextState, push = false, reason = "作業終了")
                    pushStatusAsync(reason = "session-end")
                }
            } else {
                withContext(Dispatchers.Main) {
                    postLog("作業終了の通知に失敗: ${result.exceptionOrNull()?.message}")
                }
            }
        }
    }

    private fun handleRecordingStart() {
        val target = when (currentState) {
            WorkState.IDLE -> WorkState.RECORDING
            WorkState.WORKING -> WorkState.WORKING_RECORDING
            WorkState.BREAK -> WorkState.BREAK_RECORDING
            WorkState.RECORDING, WorkState.WORKING_RECORDING, WorkState.BREAK_RECORDING -> {
                postLog("既に録画中です")
                return
            }
            WorkState.RECORDING_PAUSED -> WorkState.RECORDING
        }
        transitionTo(target, reason = "録画開始")
    }

    private fun handleRecordingStop() {
        val target = when (currentState) {
            WorkState.RECORDING -> WorkState.IDLE
            WorkState.WORKING_RECORDING -> WorkState.WORKING
            WorkState.BREAK_RECORDING -> WorkState.BREAK
            WorkState.RECORDING_PAUSED -> WorkState.IDLE
            else -> {
                postLog("録画は開始されていません")
                return
            }
        }
        transitionTo(target, reason = "録画停止")
    }

    private fun logStatus() {
        val session = currentSessionId?.toString() ?: "なし"
        postLog("状態: ${currentState.displayName} / セッション: ${session} / ストリーミング: ${if (isStreaming) "ON" else "OFF"}")
    }

    private fun requestSessionStatus() {
        val sessionId = currentSessionId ?: return postLog("アクティブなセッションがありません")
        scope.launch {
            val result = backend.getSession(sessionId)
            if (result.isSuccess) {
                val response = result.getOrNull()
                withContext(Dispatchers.Main) {
                    postLog("セッション確認: status=${response?.status} started=${response?.startedAt} ended=${response?.endedAt}")
                }
            } else {
                withContext(Dispatchers.Main) {
                    postLog("セッション確認失敗: ${result.exceptionOrNull()?.message}")
                }
            }
        }
    }

    private fun transitionTo(state: WorkState, reason: String, push: Boolean = true) {
        if (currentState == state) return
        currentState = state
        scope.launch(Dispatchers.Main) {
            onLog("状態遷移: ${state.displayName} (${reason})")
            onStateChanged(state)
            if (push) pushStatusAsync(reason = reason)
        }
    }

    private fun pushStatusAsync(reason: String) {
        scope.launch {
            val payload = DeviceStatusPayload(
                deviceIdentifier = deviceIdentifier,
                state = currentState.name,
                batteryLevel = lastBatteryLevel,
                temperatureC = lastTemperatureC,
                networkQuality = lastNetworkQuality,
                isStreaming = isStreaming,
                sessionId = currentSessionId?.toString(),
                timestamp = timestampFormatter.format(Instant.now()),
                metadata = mapOf("reason" to reason)
            )
            backend.postDeviceStatus(AppConfig.getDeviceName(context), payload)
        }
    }
}

enum class WorkState(val displayName: String) {
    IDLE("待機"),
    WORKING("作業中"),
    BREAK("休憩中"),
    RECORDING("録画中"),
    WORKING_RECORDING("作業+録画"),
    BREAK_RECORDING("休憩+録画"),
    RECORDING_PAUSED("録画一時停止");

    val isRecording: Boolean
        get() = when (this) {
            RECORDING, WORKING_RECORDING, BREAK_RECORDING -> true
            else -> false
        }
}
