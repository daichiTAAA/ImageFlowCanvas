package com.imageflow.kmp.network

import com.imageflow.kmp.network.ktor.AndroidNetworkDiagnosticClient

actual object PlatformNetworkDiagnostics {
    actual suspend fun testConnection(url: String): PlatformDiagnosticResult {
        val diagnosticClient = AndroidNetworkDiagnosticClient()
        val result = diagnosticClient.testConnection(url)
        
        return PlatformDiagnosticResult(
            success = result.success,
            message = result.message,
            details = result.responseBody?.take(500) // First 500 chars for preview
        )
    }
}