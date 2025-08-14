package com.imageflow.kmp.settings

import android.content.Context
import com.imageflow.kmp.database.AndroidDbContextHolder

actual object AppSettings {
    private const val PREFS = "imageflow_settings"
    private const val KEY_BASE_URL = "api_base_url"

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
}

