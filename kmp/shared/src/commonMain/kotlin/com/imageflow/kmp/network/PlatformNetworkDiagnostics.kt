package com.imageflow.kmp.network

data class PlatformDiagnosticResult(
    val success: Boolean,
    val message: String,
    val details: String? = null
)

expect object PlatformNetworkDiagnostics {
    suspend fun testConnection(url: String): PlatformDiagnosticResult
}