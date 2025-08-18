package com.imageflow.kmp.network

import kotlinx.serialization.Serializable

interface AuthApiService {
    suspend fun login(username: String, password: String): ApiResult<LoginResponse>
    suspend fun logout(): ApiResult<Boolean>
    suspend fun me(): ApiResult<Boolean>
}

@Serializable
data class LoginResponse(
    val access_token: String,
    val token_type: String = "bearer",
    val expires_in: Int
)
