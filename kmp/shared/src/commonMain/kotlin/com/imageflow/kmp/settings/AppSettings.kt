package com.imageflow.kmp.settings

// Simple expect/actual storage for persisting small app settings (e.g., API base URL)
expect object AppSettings {
    fun getBaseUrl(): String?
    fun setBaseUrl(url: String)
    fun getProcessCode(): String?
    fun setProcessCode(code: String)
    fun getAuthToken(): String?
    fun setAuthToken(token: String?)
}
