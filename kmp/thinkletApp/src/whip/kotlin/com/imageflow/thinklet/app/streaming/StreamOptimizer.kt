package com.imageflow.thinklet.app.streaming

import com.imageflow.thinklet.app.command.WorkState

/**
 * Lightweight heuristic quality manager for THINKLET streaming.
 * It intentionally keeps the model simple so that we can evolve it with real telemetry later.
 */
class StreamOptimizer {
    fun decide(
        batteryLevel: Int?,
        networkQuality: String?,
        workState: WorkState,
    ): StreamingDecision {
        val normalizedQuality = networkQuality?.lowercase()?.trim()
        val battery = batteryLevel ?: 100

        val codecPreference = when {
            normalizedQuality == "poor" || normalizedQuality == "bad" -> listOf(StreamCodec.H264, StreamCodec.H265)
            battery < 25 -> listOf(StreamCodec.H265, StreamCodec.H264)
            else -> listOf(StreamCodec.H265, StreamCodec.H264)
        }

        val resolution = when {
            battery < 15 -> Resolution.HD_540
            normalizedQuality == "poor" -> Resolution.HD_540
            normalizedQuality == "fair" -> Resolution.HD_720
            workState.isRecording -> Resolution.HD_1080
            else -> Resolution.HD_720
        }

        val bitrate = when (resolution) {
            Resolution.HD_1080 -> 2_500_000..4_000_000
            Resolution.HD_720 -> 1_500_000..2_500_000
            Resolution.HD_540 -> 900_000..1_500_000
        }

        return StreamingDecision(
            codecPreference = codecPreference,
            resolution = resolution,
            bitrateRange = bitrate,
        )
    }
}

data class StreamingDecision(
    val codecPreference: List<StreamCodec>,
    val resolution: Resolution,
    val bitrateRange: IntRange,
)

enum class StreamCodec(val sdpName: String) {
    H264("H264"),
    H265("H265");
}

enum class Resolution(val width: Int, val height: Int, val fps: Int = 30) {
    HD_1080(1920, 1080),
    HD_720(1280, 720),
    HD_540(960, 540);
}
