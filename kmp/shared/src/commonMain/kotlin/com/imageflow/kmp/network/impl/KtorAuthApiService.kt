package com.imageflow.kmp.network.impl

import com.imageflow.kmp.network.*
import kotlinx.serialization.json.Json
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.Serializable

class KtorAuthApiService(
    private val rest: RestClient,
    private val json: Json = Json { ignoreUnknownKeys = true; isLenient = true }
) : AuthApiService {
    @Serializable
    private data class LoginReq(val username: String, val password: String)
    override suspend fun login(username: String, password: String): ApiResult<LoginResponse> =
        runCatching {
            val body = json.encodeToString(LoginReq(username, password))
            val respText = rest.postJson("auth/login", body)
            val resp = json.decodeFromString<LoginResponse>(respText)
            ApiResult.Success(resp)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }

    override suspend fun logout(): ApiResult<Boolean> = ApiResult.Success(true)

    override suspend fun me(): ApiResult<Boolean> =
        runCatching {
            // Returns 200 with user info if token valid; otherwise 401
            rest.get("auth/me")
            ApiResult.Success(true)
        }.getOrElse { e -> ApiResult.NetworkError(e.message ?: "Network error") }
}
