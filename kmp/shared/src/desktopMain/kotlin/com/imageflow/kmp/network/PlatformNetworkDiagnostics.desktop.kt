package com.imageflow.kmp.network

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.statement.HttpResponse
import io.ktor.http.isSuccess

actual object PlatformNetworkDiagnostics {
    actual suspend fun testConnection(url: String): PlatformDiagnosticResult {
        // Desktop implementation - similar to iOS, simpler than Android
        val client = HttpClient()
        
        return try {
            val startTime = System.currentTimeMillis()
            val response: HttpResponse = client.get(url)
            val duration = System.currentTimeMillis() - startTime
            
            if (response.status.isSuccess()) {
                val responseBody = response.body<String>()
                PlatformDiagnosticResult(
                    success = true,
                    message = "Desktop connection succeeded in ${duration}ms",
                    details = responseBody.take(500)
                )
            } else {
                PlatformDiagnosticResult(
                    success = false,
                    message = "Desktop connection failed: HTTP ${response.status.value} (${duration}ms)",
                    details = null
                )
            }
        } catch (e: Exception) {
            PlatformDiagnosticResult(
                success = false,
                message = "Desktop connection error: ${e.message ?: e::class.simpleName}",
                details = null
            )
        } finally {
            client.close()
        }
    }
}