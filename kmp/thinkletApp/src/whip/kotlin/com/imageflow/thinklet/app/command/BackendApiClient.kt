package com.imageflow.thinklet.app.command

import android.content.Context
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.imageflow.thinklet.app.AppConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import java.io.IOException
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.util.UUID
import java.util.concurrent.TimeUnit

class BackendApiClient(context: Context) {

    private val baseUrl = AppConfig.getBackendUrl(context).trimEnd('/')
    private val gson = Gson()
    private val formatter = DateTimeFormatter.ISO_INSTANT

    private val http = OkHttpClient.Builder()
        .callTimeout(8, TimeUnit.SECONDS)
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .writeTimeout(8, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        })
        .build()

    suspend fun postWorkStart(payload: WorkCommandPayload.Start): Result<WorkSessionResponse> {
        return postJson("/v1/thinklet/work-sessions/start", payload, WorkSessionResponse::class.java)
    }

    suspend fun postWorkEnd(payload: WorkCommandPayload.End): Result<WorkSessionResponse> {
        return postJson("/v1/thinklet/work-sessions/end", payload, WorkSessionResponse::class.java)
    }

    suspend fun postDeviceStatus(deviceName: String, payload: DeviceStatusPayload): Result<Unit> {
        val path = "/v1/thinklet/devices/${deviceName}/status"
        return postVoid(path, payload)
    }

    suspend fun getSession(sessionId: UUID): Result<WorkSessionResponse> {
        return withContext(Dispatchers.IO) {
            val request = Request.Builder()
                .url("${baseUrl}/v1/thinklet/work-sessions/${sessionId}")
                .get()
                .build()
            try {
                http.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        return@withContext Result.failure(IOException("HTTP ${response.code}"))
                    }
                    val body = response.body?.string().orEmpty()
                    val parsed = gson.fromJson(body, WorkSessionResponse::class.java)
                    Result.success(parsed)
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    private suspend fun <T> postJson(path: String, payload: Any, clazz: Class<T>): Result<T> {
        return withContext(Dispatchers.IO) {
            val url = "${baseUrl}${path}"
            val json = gson.toJson(payload)
            val body = json.toRequestBody(JSON_MEDIA_TYPE)
            val request = Request.Builder().url(url).post(body).build()
            try {
                http.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        return@withContext Result.failure(IOException("HTTP ${response.code}"))
                    }
                    val responseBody = response.body?.string().orEmpty()
                    val parsed = gson.fromJson(responseBody, clazz)
                    Result.success(parsed)
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    private suspend fun postVoid(path: String, payload: Any): Result<Unit> {
        return withContext(Dispatchers.IO) {
            val url = "${baseUrl}${path}"
            val json = gson.toJson(payload)
            val body = json.toRequestBody(JSON_MEDIA_TYPE)
            val request = Request.Builder().url(url).post(body).build()
            try {
                http.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        return@withContext Result.failure(IOException("HTTP ${response.code}"))
                    }
                    Result.success(Unit)
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun buildStartPayload(
        deviceName: String,
            deviceIdentifier: String?,
            command: VoiceCommand,
            sessionHint: UUID?,
            batteryLevel: Int?,
            networkQuality: String?,
            temperatureC: Double?,
    ): WorkCommandPayload.Start {
        return WorkCommandPayload.Start(
            deviceName = deviceName,
            deviceIdentifier = deviceIdentifier,
            command = command.action.name,
            normalizedCommand = command.normalizedText.takeIf { it.isNotBlank() },
            recognizedText = command.rawText.takeIf { it.isNotBlank() },
            confidence = command.confidence,
            startedAt = formatter.format(command.timestamp),
            sessionHint = sessionHint?.toString(),
            networkQuality = networkQuality,
            batteryLevel = batteryLevel,
            temperatureC = temperatureC,
        )
    }

    suspend fun buildEndPayload(
        sessionId: UUID?,
        deviceName: String,
        command: VoiceCommand,
        batteryLevel: Int?,
        networkQuality: String?,
        temperatureC: Double?,
    ): WorkCommandPayload.End {
        return WorkCommandPayload.End(
            sessionId = sessionId?.toString(),
            deviceName = deviceName,
            command = command.action.name,
            normalizedCommand = command.normalizedText.takeIf { it.isNotBlank() },
            recognizedText = command.rawText.takeIf { it.isNotBlank() },
            confidence = command.confidence,
            endedAt = formatter.format(command.timestamp),
            networkQuality = networkQuality,
            batteryLevel = batteryLevel,
            temperatureC = temperatureC,
        )
    }

    companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
    }
}

sealed interface WorkCommandPayload {
    data class Start(
        @SerializedName("deviceName") val deviceName: String,
        @SerializedName("deviceIdentifier") val deviceIdentifier: String?,
        @SerializedName("command") val command: String,
        @SerializedName("normalizedCommand") val normalizedCommand: String?,
        @SerializedName("recognizedText") val recognizedText: String?,
        @SerializedName("confidence") val confidence: Float,
        @SerializedName("startedAt") val startedAt: String,
        @SerializedName("sessionHint") val sessionHint: String?,
        @SerializedName("networkQuality") val networkQuality: String?,
        @SerializedName("batteryLevel") val batteryLevel: Int?,
        @SerializedName("temperatureC") val temperatureC: Double?,
        @SerializedName("metadata") val metadata: Map<String, Any?>? = null,
    ) : WorkCommandPayload

    data class End(
        @SerializedName("sessionId") val sessionId: String?,
        @SerializedName("deviceName") val deviceName: String,
        @SerializedName("command") val command: String,
        @SerializedName("normalizedCommand") val normalizedCommand: String?,
        @SerializedName("recognizedText") val recognizedText: String?,
        @SerializedName("confidence") val confidence: Float,
        @SerializedName("endedAt") val endedAt: String,
        @SerializedName("networkQuality") val networkQuality: String?,
        @SerializedName("batteryLevel") val batteryLevel: Int?,
        @SerializedName("temperatureC") val temperatureC: Double?,
        @SerializedName("metadata") val metadata: Map<String, Any?>? = null,
    ) : WorkCommandPayload
}

data class WorkSessionResponse(
    @SerializedName("sessionId") val sessionId: String,
    @SerializedName("deviceName") val deviceName: String,
    @SerializedName("status") val status: String,
    @SerializedName("startedAt") val startedAt: String,
    @SerializedName("endedAt") val endedAt: String?,
    @SerializedName("lastEvent") val lastEvent: String?,
)

data class DeviceStatusPayload(
    @SerializedName("deviceIdentifier") val deviceIdentifier: String?,
    @SerializedName("state") val state: String,
    @SerializedName("batteryLevel") val batteryLevel: Int?,
    @SerializedName("temperatureC") val temperatureC: Double?,
    @SerializedName("networkQuality") val networkQuality: String?,
    @SerializedName("isStreaming") val isStreaming: Boolean,
    @SerializedName("sessionId") val sessionId: String?,
    @SerializedName("timestamp") val timestamp: String,
    @SerializedName("metadata") val metadata: Map<String, Any?>? = null,
)
