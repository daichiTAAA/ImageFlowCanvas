package com.imageflow.kmp.network.ktor

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import com.imageflow.kmp.network.RestClient

expect fun createHttpClient(): HttpClient

class BasicRestClient(
    private val httpClient: HttpClient,
    private val baseSupplier: () -> String,
) : RestClient {
    override suspend fun get(urlPath: String): String {
        val base = baseSupplier().trimEnd('/')
        val path = urlPath.trimStart('/')
        return httpClient.get("${'$'}base/${'$'}path").body()
    }
}
