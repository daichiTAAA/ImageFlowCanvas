package com.imageflow.thinklet.app

import android.content.Context
import android.net.Uri
import android.provider.Settings

object AppConfig {
    private const val PREFS = "thinklet_prefs"
    private const val KEY_URL = "whip.url"
    private const val KEY_AUTO = "auto.start"
    private const val KEY_AUTO_RESUME = "auto.resume"

    fun getWhipUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY_URL, null)
        if (!existing.isNullOrBlank()) {
            val migrated = existing.replace("/whip/mobile/", "/whip/uplink/").replace("/whip/thinklet/", "/whip/uplink/")
            val sanitized = sanitizeWhipUrl(context, migrated)
            if (sanitized != existing) {
                prefs.edit().putString(KEY_URL, sanitized).apply()
            }
            return sanitized
        }
        val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        return "http://192.168.0.5:8889/whip/uplink/${deviceId}"
    }

    fun setWhipUrl(context: Context, url: String) {
        val normalized = sanitizeWhipUrl(context, url)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_URL, normalized).apply()
    }

    fun getAutoStart(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getBoolean(KEY_AUTO, true)
    }

    fun setAutoStart(context: Context, auto: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_AUTO, auto).apply()
    }

    fun getAutoResume(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getBoolean(KEY_AUTO_RESUME, true)
    }

    fun setAutoResume(context: Context, auto: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_AUTO_RESUME, auto).apply()
    }

    fun sanitizeWhipUrl(context: Context, raw: String?): String {
        val trimmed = raw?.trim() ?: return ""
        if (trimmed.isEmpty()) return trimmed
        return try {
            val parsed = Uri.parse(trimmed)
            if (parsed.scheme.isNullOrBlank() || parsed.host.isNullOrBlank()) {
                trimmed
            } else {
                val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
                val segments = parsed.pathSegments ?: emptyList()
                val slug = segments.getOrNull(1)
                val currentId = if (segments.size >= 3 && segments[0] == "whip" && slug in setOf("uplink", "thinklet", "mobile")) {
                    segments[2].ifBlank { deviceId }
                } else {
                    null
                }
                val builder = Uri.Builder().scheme(parsed.scheme)
                val authority = parsed.encodedAuthority ?: run {
                    val host = parsed.host ?: ""
                    val port = if (parsed.port != -1) ":${parsed.port}" else ""
                    host + port
                }
                if (authority.isNotBlank()) builder.encodedAuthority(authority)
                builder.encodedPath("/whip/uplink/${currentId ?: deviceId}")
                if (!parsed.encodedQuery.isNullOrBlank()) builder.encodedQuery(parsed.encodedQuery)
                if (!parsed.fragment.isNullOrBlank()) builder.fragment(parsed.fragment)
                builder.build().toString()
            }
        } catch (_: Exception) {
            trimmed
        }
    }
}
