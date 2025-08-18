package com.imageflow.kmp.settings

import java.util.prefs.Preferences

actual object AppSettings {
    private val prefs: Preferences = Preferences.userRoot().node("com.imageflow.kmp")
    private const val KEY_BASE_URL = "api_base_url"
    private const val KEY_PROCESS_CODE = "process_code"
    private const val KEY_AUTH_TOKEN = "auth_token"
    private const val KEY_AUTH_USERNAME = "auth_username"
    private const val KEY_AUTH_PASSWORD = "auth_password"

    actual fun getBaseUrl(): String? = prefs.get(KEY_BASE_URL, null)

    actual fun setBaseUrl(url: String) {
        prefs.put(KEY_BASE_URL, url)
    }

    actual fun getProcessCode(): String? = prefs.get(KEY_PROCESS_CODE, null)
    actual fun setProcessCode(code: String) { prefs.put(KEY_PROCESS_CODE, code) }

    actual fun getAuthToken(): String? = prefs.get(KEY_AUTH_TOKEN, null)
    actual fun setAuthToken(token: String?) {
        if (token == null) prefs.remove(KEY_AUTH_TOKEN) else prefs.put(KEY_AUTH_TOKEN, token)
    }
    actual fun getAuthUsername(): String? = prefs.get(KEY_AUTH_USERNAME, null)
    actual fun getAuthPassword(): String? = prefs.get(KEY_AUTH_PASSWORD, null)
    actual fun setAuthCredentials(username: String, password: String) {
        prefs.put(KEY_AUTH_USERNAME, username)
        prefs.put(KEY_AUTH_PASSWORD, password)
    }
    actual fun clearAuthCredentials() {
        prefs.remove(KEY_AUTH_USERNAME)
        prefs.remove(KEY_AUTH_PASSWORD)
    }
}
