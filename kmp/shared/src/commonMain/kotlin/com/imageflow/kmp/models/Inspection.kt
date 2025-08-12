package com.imageflow.kmp.models

data class Inspection(
    val id: String,
    val productId: String,
    val result: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
    val synced: Boolean = false,
)

