package com.imageflow.kmp.network

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.statement.HttpResponse
import io.ktor.http.isSuccess

actual object PlatformNetworkDiagnostics {
    actual suspend fun testConnection(url: String): PlatformDiagnosticResult {
        // iOS implementation - simpler since iOS doesn't have the same proxy issues
        val client = HttpClient()
        
        return try {
            val startTime = System.currentTimeMillis()
            val response: HttpResponse = client.get(url)
            val duration = System.currentTimeMillis() - startTime
            
            if (response.status.isSuccess()) {
                val responseBody = response.body<String>()
                PlatformDiagnosticResult(
                    success = true,
                    message = "iOS connection succeeded in ${duration}ms",
                    details = responseBody.take(500)
                )
            } else {
                PlatformDiagnosticResult(
                    success = false,
                    message = "iOS connection failed: HTTP ${response.status.value} (${duration}ms)",
                    details = null
                )
            }
        } catch (e: Exception) {
            PlatformDiagnosticResult(
                success = false,
                message = "iOS connection error: ${e.message ?: e::class.simpleName}",
                details = null
            )
        } finally {
            client.close()
        }
    }
}