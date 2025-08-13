package com.imageflow.kmp.network.ktor

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.client.request.get
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import com.imageflow.kmp.network.RestClient

fun createHttpClient(): HttpClient = HttpClient {
    install(WebSockets)
    install(ContentNegotiation) {
        json(Json { ignoreUnknownKeys = true; isLenient = true })
    }
    install(Logging) { level = LogLevel.INFO }
}

class BasicRestClient(
    private val httpClient: HttpClient,
    private val baseUrl: String,
) : RestClient {
    override suspend fun get(urlPath: String): String =
        httpClient.get("${'$'}baseUrl/${'$'}urlPath").body()
}

