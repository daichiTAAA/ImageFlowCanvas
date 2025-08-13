package com.imageflow.kmp.qr

// Product info fields aligned with docs:
// - 指図番号: workOrderId
// - 指示番号: instructionId
// - 型式: productType
// - 機番: machineNumber
// - 生産年月日: productionDate (ISO-8601 string)
// - 月連番: monthlySequence
data class DecodedProductInfo(
    val workOrderId: String?,
    val instructionId: String?,
    val productType: String?,
    val machineNumber: String?,
    val productionDate: String?,
    val monthlySequence: Int?,
)

interface BarcodeDecoder {
    fun decode(raw: String): DecodedProductInfo
}
