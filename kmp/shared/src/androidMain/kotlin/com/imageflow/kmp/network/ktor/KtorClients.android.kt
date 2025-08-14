package com.imageflow.kmp.network.ktor

import io.ktor.client.HttpClient
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.serialization.kotlinx.json.json
import io.ktor.client.engine.okhttp.OkHttp
import java.net.Proxy
import kotlinx.serialization.json.Json

actual fun createHttpClient(): HttpClient = HttpClient(OkHttp) {
    engine {
        config {
            // Ignore system proxy (some devices set localhost:80 proxy and break dev)
            proxy(Proxy.NO_PROXY)
        }
    }
    install(WebSockets)
    install(ContentNegotiation) {
        json(Json { ignoreUnknownKeys = true; isLenient = true })
    }
    install(Logging) { level = LogLevel.INFO }
}

