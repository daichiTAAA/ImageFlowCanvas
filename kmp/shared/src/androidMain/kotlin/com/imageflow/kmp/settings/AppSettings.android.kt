package com.imageflow.kmp.settings

import android.content.Context
import com.imageflow.kmp.database.AndroidDbContextHolder

actual object AppSettings {
    private const val PREFS = "imageflow_settings"
    private const val KEY_BASE_URL = "api_base_url"
    private const val KEY_PROCESS_CODE = "process_code"
    private const val KEY_AUTH_TOKEN = "auth_token"
    private const val KEY_AUTH_USERNAME = "auth_username"
    private const val KEY_AUTH_PASSWORD = "auth_password"

    private fun ctx(): Context = AndroidDbContextHolder.context

    actual fun getBaseUrl(): String? {
        return try {
            ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_BASE_URL, null)
        } catch (_: Exception) {
            null
        }
    }

    actual fun setBaseUrl(url: String) {
        try {
            ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_BASE_URL, url)
                .apply()
        } catch (_: Exception) {
            // ignore
        }
    }

    actual fun getProcessCode(): String? {
        return try {
            ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_PROCESS_CODE, null)
        } catch (_: Exception) {
            null
        }
    }

    actual fun setProcessCode(code: String) {
        try {
            ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_PROCESS_CODE, code)
                .apply()
        } catch (_: Exception) {
            // ignore
        }
    }

    actual fun getAuthToken(): String? {
        return try {
            ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_AUTH_TOKEN, null)
        } catch (_: Exception) { null }
    }

    actual fun setAuthToken(token: String?) {
        try {
            val edit = ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            if (token == null) edit.remove(KEY_AUTH_TOKEN) else edit.putString(KEY_AUTH_TOKEN, token)
            edit.apply()
        } catch (_: Exception) { }
    }

    actual fun getAuthUsername(): String? {
        return try { ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_AUTH_USERNAME, null) } catch (_: Exception) { null }
    }
    actual fun getAuthPassword(): String? {
        return try { ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_AUTH_PASSWORD, null) } catch (_: Exception) { null }
    }
    actual fun setAuthCredentials(username: String, password: String) {
        try {
            ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .putString(KEY_AUTH_USERNAME, username)
                .putString(KEY_AUTH_PASSWORD, password)
                .apply()
        } catch (_: Exception) {}
    }
    actual fun clearAuthCredentials() {
        try {
            ctx().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .remove(KEY_AUTH_USERNAME)
                .remove(KEY_AUTH_PASSWORD)
                .apply()
        } catch (_: Exception) {}
    }
}
