package com.imageflow.kmp.network

interface RestClient {
    suspend fun get(urlPath: String): String
    suspend fun postJson(urlPath: String, jsonBody: String): String
    suspend fun postMultipartBytes(
        urlPath: String,
        fieldName: String,
        filename: String,
        bytes: ByteArray,
        contentType: String
    ): String
}
