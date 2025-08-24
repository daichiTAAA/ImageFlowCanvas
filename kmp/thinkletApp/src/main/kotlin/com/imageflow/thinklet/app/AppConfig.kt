package com.imageflow.thinklet.app

import android.content.Context
import android.provider.Settings

object AppConfig {
    private const val PREFS = "thinklet_prefs"
    private const val KEY_URL = "whip.url"
    private const val KEY_AUTO = "auto.start"

    fun getWhipUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY_URL, null)
        if (!existing.isNullOrBlank()) return existing
        val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        return "http://192.168.0.9:8889/whip/thinklet/${deviceId}"
    }

    fun setWhipUrl(context: Context, url: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_URL, url).apply()
    }

    fun getAutoStart(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getBoolean(KEY_AUTO, true)
    }

    fun setAutoStart(context: Context, auto: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_AUTO, auto).apply()
    }
}

