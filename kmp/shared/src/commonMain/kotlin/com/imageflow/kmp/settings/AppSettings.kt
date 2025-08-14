package com.imageflow.kmp.settings

// Simple expect/actual storage for persisting small app settings (e.g., API base URL)
expect object AppSettings {
    fun getBaseUrl(): String?
    fun setBaseUrl(url: String)
}

