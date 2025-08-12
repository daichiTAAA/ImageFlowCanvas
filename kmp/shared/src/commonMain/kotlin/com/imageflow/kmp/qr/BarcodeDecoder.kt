package com.imageflow.kmp.qr

data class DecodedProductInfo(
    val id: String?,
    val model: String?,
    val serialNumber: String?,
)

interface BarcodeDecoder {
    fun decode(raw: String): DecodedProductInfo
}

