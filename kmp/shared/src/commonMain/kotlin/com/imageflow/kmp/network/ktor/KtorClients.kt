package com.imageflow.kmp.network.ktor

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.statement.HttpResponse
import io.ktor.http.isSuccess
import com.imageflow.kmp.network.RestClient

expect fun createHttpClient(): HttpClient

class BasicRestClient(
    private val httpClient: HttpClient,
    private val baseSupplier: () -> String,
) : RestClient {
    override suspend fun get(urlPath: String): String {
        val base = baseSupplier().trimEnd('/')
        val path = urlPath.trimStart('/')
        val finalUrl = "${'$'}base/${'$'}path"
        
        try {
            println("RestClient: Attempting GET request to: ${'$'}finalUrl")
            val response: HttpResponse = httpClient.get(finalUrl)
            
            println("RestClient: Response status: ${'$'}{response.status}")
            println("RestClient: Response headers: ${'$'}{response.headers}")
            
            if (!response.status.isSuccess()) {
                val errorBody = try {
                    response.body<String>()
                } catch (e: Exception) {
                    "Unable to read error body: ${'$'}{e.message}"
                }
                throw Exception("HTTP ${'$'}{response.status.value} ${'$'}{response.status.description}: ${'$'}errorBody")
            }
            
            val responseBody = response.body<String>()
            println("RestClient: Success - received ${'$'}{responseBody.length} characters")
            return responseBody
            
        } catch (e: Exception) {
            println("RestClient: Error for URL ${'$'}finalUrl: ${'$'}{e.message}")
            // Re-throw with more context about the URL that failed
            throw Exception("Failed to connect to ${'$'}finalUrl: ${'$'}{e.message}", e)
        }
    }
}
