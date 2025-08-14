package com.imageflow.kmp.network.ktor

import io.ktor.client.HttpClient
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.defaultRequest
import io.ktor.serialization.kotlinx.json.json
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.http.ContentType
import io.ktor.http.contentType
import java.net.Proxy
import kotlinx.serialization.json.Json
import java.util.concurrent.TimeUnit

actual fun createHttpClient(): HttpClient = HttpClient(OkHttp) {
    engine {
        config {
            // Completely disable proxy usage to prevent localhost:80 redirects
            proxy(Proxy.NO_PROXY)
            
            // Disable system property-based proxy configurations
            System.setProperty("http.proxyHost", "")
            System.setProperty("http.proxyPort", "")
            System.setProperty("https.proxyHost", "")
            System.setProperty("https.proxyPort", "")
            
            // Set connection timeouts to detect issues faster
            connectTimeout(30, TimeUnit.SECONDS)
            readTimeout(30, TimeUnit.SECONDS)
            writeTimeout(30, TimeUnit.SECONDS)
            
            // Force use of system DNS to avoid proxy DNS issues
            followRedirects(false) // Disable redirects to catch localhost:80 redirects
        }
    }
    
    install(HttpTimeout) {
        requestTimeoutMillis = 30000
        connectTimeoutMillis = 30000
        socketTimeoutMillis = 30000
    }
    
    install(WebSockets)
    install(ContentNegotiation) {
        json(Json { 
            ignoreUnknownKeys = true
            isLenient = true
        })
    }
    
    install(Logging) { 
        level = LogLevel.ALL // More verbose logging for debugging
    }
    
    defaultRequest {
        contentType(ContentType.Application.Json)
    }
}

