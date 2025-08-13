package com.imageflow.kmp.models

// Canonical product info used across KMP, matching QR decode fields
data class ProductInfo(
    val workOrderId: String,
    val instructionId: String,
    val productType: String,
    val machineNumber: String,
    val productionDate: String, // ISO-8601 (YYYY-MM-DD)
    val monthlySequence: Int,
)

