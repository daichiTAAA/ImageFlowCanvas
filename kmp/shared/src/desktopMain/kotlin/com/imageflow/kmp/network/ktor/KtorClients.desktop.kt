package com.imageflow.kmp.network.ktor

import io.ktor.client.HttpClient
import io.ktor.client.engine.cio.CIO
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.client.plugins.HttpTimeout
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import io.ktor.http.HttpHeaders
import io.ktor.client.request.header

actual fun createHttpClient(): HttpClient = HttpClient(CIO) {
    // Avoid OS/JVM proxy interference on desktop
    try {
        System.setProperty("java.net.useSystemProxies", "false")
        System.setProperty("http.proxyHost", "")
        System.setProperty("http.proxyPort", "")
        System.setProperty("https.proxyHost", "")
        System.setProperty("https.proxyPort", "")
        System.setProperty("http.nonProxyHosts", "*")
    } catch (_: Exception) {}
    install(WebSockets)
    install(ContentNegotiation) {
        json(Json { ignoreUnknownKeys = true; isLenient = true })
    }
    install(Logging) { level = LogLevel.INFO }
    
    install(HttpTimeout) {
        requestTimeoutMillis = 7000
        connectTimeoutMillis = 3000
        socketTimeoutMillis = 7000
    }

    // Default headers for all requests (Authorization when available)
    defaultRequest {
        val token = try { com.imageflow.kmp.di.DependencyContainer.currentAuthToken() } catch (_: Exception) { null }
        if (!token.isNullOrBlank()) header(HttpHeaders.Authorization, "Bearer $token")
    }
}
