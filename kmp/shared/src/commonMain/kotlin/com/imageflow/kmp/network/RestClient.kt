package com.imageflow.kmp.network

interface RestClient {
    suspend fun get(urlPath: String): String
    suspend fun postJson(urlPath: String, jsonBody: String): String
}
