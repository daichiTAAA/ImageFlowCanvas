package com.imageflow.kmp.settings

import java.util.prefs.Preferences

actual object AppSettings {
    private val prefs: Preferences = Preferences.userRoot().node("com.imageflow.kmp")
    private const val KEY_BASE_URL = "api_base_url"

    actual fun getBaseUrl(): String? = prefs.get(KEY_BASE_URL, null)

    actual fun setBaseUrl(url: String) {
        prefs.put(KEY_BASE_URL, url)
    }
}

