package com.imageflow.kmp.models

import kotlinx.serialization.Serializable
import com.imageflow.kmp.state.InspectionState

// Enhanced inspection model based on F-022, F-023, F-024 requirements
@Serializable
data class Inspection(
    val id: String,
    val productId: String,
    val workOrderId: String,
    val instructionId: String,
    val inspectionType: InspectionType,
    val inspectionState: InspectionState = InspectionState.ProductScanning,
    val aiResult: AiInspectionResult? = null,
    val aiConfidence: Float? = null,
    val humanVerified: Boolean = false,
    val humanResult: HumanResult? = null,
    val humanComments: String? = null,
    val inspectorId: String? = null,
    val startedAt: Long,
    val completedAt: Long? = null,
    val imagePaths: List<String> = emptyList(),
    val videoPath: String? = null,
    val metadata: InspectionMetadata? = null,
    val synced: Boolean = false,
    val syncAttempts: Int = 0,
    val lastSyncAttempt: Long? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)

@Serializable
enum class InspectionType {
    STATIC_IMAGE,   // 静止画検査
    VIDEO,          // 動画検査
    REALTIME        // リアルタイム検査（THINKLETなど）
}

@Serializable
data class AiInspectionResult(
    val overallResult: InspectionResult,
    val detectedDefects: List<DetectedDefect> = emptyList(),
    val measurements: List<Measurement> = emptyList(),
    val confidence: Float,
    val processingTimeMs: Long,
    val pipelineId: String? = null
)

@Serializable
data class DetectedDefect(
    val type: DefectType,
    val location: BoundingBox,
    val severity: DefectSeverity,
    val confidence: Float,
    val description: String? = null
)

@Serializable
enum class DefectType {
    SURFACE_DAMAGE,     // 表面損傷
    CONTAMINATION,      // 汚れ
    DEFORMATION,        // 変形
    COLOR_ANOMALY,      // 色異常
    DIMENSIONAL_ERROR,  // 寸法異常
    TEXT_ERROR,         // 文字認識エラー
    OTHER
}

@Serializable
enum class DefectSeverity {
    CRITICAL,   // 致命的
    MAJOR,      // 重大
    MINOR,      // 軽微
    INFO        // 情報のみ
}

@Serializable
data class BoundingBox(
    val x: Float,
    val y: Float,
    val width: Float,
    val height: Float
)

@Serializable
data class Measurement(
    val type: MeasurementType,
    val value: Float,
    val unit: String,
    val tolerance: FloatRange? = null,
    val withinTolerance: Boolean = true
)

@Serializable
enum class MeasurementType {
    LENGTH,     // 長さ
    WIDTH,      // 幅
    HEIGHT,     // 高さ
    DIAMETER,   // 直径
    AREA,       // 面積
    ANGLE,      // 角度
    COLOR_DIFF  // 色差
}

@Serializable
data class FloatRange(
    val min: Float,
    val max: Float
)

@Serializable
enum class HumanResult {
    OK,         // 合格
    NG,         // 不合格
    PENDING     // 保留
}

@Serializable
enum class InspectionResult {
    PASS,       // 合格
    FAIL,       // 不合格
    WARNING,    // 警告
    PENDING     // 保留・要確認
}

@Serializable
data class InspectionMetadata(
    val deviceId: String? = null,
    val deviceType: String? = null,
    val location: Location? = null,
    val environmentalConditions: Map<String, String> = emptyMap(),
    val calibrationInfo: Map<String, String> = emptyMap()
)

@Serializable
data class Location(
    val latitude: Double,
    val longitude: Double,
    val altitude: Double? = null
)

