package com.imageflow.androidstream.app

import android.content.Context
import android.net.Uri
import android.provider.Settings

object AppConfig {
    private const val PREFS = "android_stream_prefs"
    private const val KEY_URL = "whip.url"
    private const val KEY_AUTO = "auto.start"
    private const val KEY_AUTO_USER_SET = "auto.start.userSet"
    private const val KEY_AUTO_RESUME = "auto.resume"

    private const val DEFAULT_BEACON_TYPE = "eddystone_uid"
    private const val DEFAULT_EDDYSTONE_NAMESPACE = "00112233445566778899"
    private const val DEFAULT_EDDYSTONE_INSTANCE = "a1b2c3d4e5f6"
    private const val DEFAULT_ENTER_SEC = 0
    private const val DEFAULT_EXIT_SEC = 1
    private const val DEFAULT_HOLD_SEC = 30

    private const val KEY_BCN_TYPE = "beacon.type"
    private const val KEY_BCN_NS = "beacon.namespace"
    private const val KEY_BCN_INST = "beacon.instance"
    private const val KEY_BCN_UUID = "beacon.uuid"
    private const val KEY_BCN_MAJOR = "beacon.major"
    private const val KEY_BCN_MINOR = "beacon.minor"
    private const val KEY_RSSI_ENTER = "privacy.enter.rssi"
    private const val KEY_RSSI_EXIT = "privacy.exit.rssi"
    private const val KEY_ENTER_SEC = "privacy.enter.seconds"
    private const val KEY_EXIT_SEC = "privacy.exit.seconds"
    private const val KEY_MATCH_STRICT = "privacy.match.strict"
    private const val KEY_HOLD_SEC = "privacy.hold.seconds"
    private const val KEY_HOLD_EXTEND_NONUID = "privacy.hold.extendNonUid"

    fun getWhipUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY_URL, null)
        if (!existing.isNullOrBlank()) {
            val migrated = existing.replace("/whip/mobile/", "/whip/thinklet/")
            val sanitized = sanitizeWhipUrl(context, migrated)
            if (sanitized != existing) {
                prefs.edit().putString(KEY_URL, sanitized).apply()
            }
            return sanitized
        }
        val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        // THINKLET backend enumerates streams under /whip/thinklet/<deviceId>
        return "http://192.168.0.5:8889/whip/thinklet/${deviceId}"
    }

    fun setWhipUrl(context: Context, url: String) {
        val normalized = sanitizeWhipUrl(context, url)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_URL, normalized)
            .apply()
    }

    fun getAutoStart(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val userSet = prefs.getBoolean(KEY_AUTO_USER_SET, false)
        val stored = prefs.getBoolean(KEY_AUTO, true)
        if (!userSet && prefs.contains(KEY_AUTO) && !stored) {
            prefs.edit().putBoolean(KEY_AUTO, true).apply()
            return true
        }
        return if (!prefs.contains(KEY_AUTO)) {
            prefs.edit().putBoolean(KEY_AUTO, true).apply()
            true
        } else {
            stored
        }
    }

    fun setAutoStart(context: Context, value: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_AUTO, value)
            .putBoolean(KEY_AUTO_USER_SET, true)
            .apply()
    }

    fun getAutoResume(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_AUTO_RESUME, true)

    fun setAutoResume(context: Context, value: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_AUTO_RESUME, value)
            .apply()
    }

    fun getBeaconType(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val stored = prefs.getString(KEY_BCN_TYPE, null)
        if (stored.isNullOrBlank()) {
            prefs.edit().putString(KEY_BCN_TYPE, DEFAULT_BEACON_TYPE).apply()
            return DEFAULT_BEACON_TYPE
        }
        return stored
    }

    fun setBeaconType(context: Context, type: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_BCN_TYPE, type)
            .apply()
    }

    fun getEddystoneNamespace(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val stored = prefs.getString(KEY_BCN_NS, null)
        if (stored.isNullOrBlank()) {
            prefs.edit().putString(KEY_BCN_NS, DEFAULT_EDDYSTONE_NAMESPACE).apply()
            return DEFAULT_EDDYSTONE_NAMESPACE
        }
        return stored
    }

    fun getEddystoneInstance(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val stored = prefs.getString(KEY_BCN_INST, null)
        if (stored.isNullOrBlank()) {
            prefs.edit().putString(KEY_BCN_INST, DEFAULT_EDDYSTONE_INSTANCE).apply()
            return DEFAULT_EDDYSTONE_INSTANCE
        }
        return stored
    }

    fun setEddystoneUid(context: Context, namespaceHex: String?, instanceHex: String?) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_BCN_NS, namespaceHex)
            .putString(KEY_BCN_INST, instanceHex)
            .apply()
    }

    fun getIBeaconUuid(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_BCN_UUID, null)

    fun getIBeaconMajor(context: Context): Int? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).let { prefs ->
            if (prefs.contains(KEY_BCN_MAJOR)) prefs.getInt(KEY_BCN_MAJOR, 0) else null
        }

    fun getIBeaconMinor(context: Context): Int? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).let { prefs ->
            if (prefs.contains(KEY_BCN_MINOR)) prefs.getInt(KEY_BCN_MINOR, 0) else null
        }

    fun setIBeacon(context: Context, uuid: String?, major: Int?, minor: Int?) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().apply {
            putString(KEY_BCN_UUID, uuid)
            if (major != null) putInt(KEY_BCN_MAJOR, major) else remove(KEY_BCN_MAJOR)
            if (minor != null) putInt(KEY_BCN_MINOR, minor) else remove(KEY_BCN_MINOR)
        }.apply()
    }

    fun getEnterRssi(context: Context): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_RSSI_ENTER, -70)

    fun setEnterRssi(context: Context, value: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_RSSI_ENTER, value)
            .apply()
    }

    fun getExitRssi(context: Context): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_RSSI_EXIT, -80)

    fun setExitRssi(context: Context, value: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_RSSI_EXIT, value)
            .apply()
    }

    fun getEnterSeconds(context: Context): Int {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!prefs.contains(KEY_ENTER_SEC)) {
            prefs.edit().putInt(KEY_ENTER_SEC, DEFAULT_ENTER_SEC).apply()
            return DEFAULT_ENTER_SEC
        }
        return prefs.getInt(KEY_ENTER_SEC, DEFAULT_ENTER_SEC)
    }

    fun setEnterSeconds(context: Context, value: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_ENTER_SEC, value)
            .apply()
    }

    fun getExitSeconds(context: Context): Int {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!prefs.contains(KEY_EXIT_SEC)) {
            prefs.edit().putInt(KEY_EXIT_SEC, DEFAULT_EXIT_SEC).apply()
            return DEFAULT_EXIT_SEC
        }
        return prefs.getInt(KEY_EXIT_SEC, DEFAULT_EXIT_SEC)
    }

    fun setExitSeconds(context: Context, value: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_EXIT_SEC, value)
            .apply()
    }

    fun isMatchStrict(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_MATCH_STRICT, true)

    fun setMatchStrict(context: Context, value: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_MATCH_STRICT, value)
            .apply()
    }

    fun getPresenceHoldSeconds(context: Context): Int {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!prefs.contains(KEY_HOLD_SEC)) {
            prefs.edit().putInt(KEY_HOLD_SEC, DEFAULT_HOLD_SEC).apply()
            return DEFAULT_HOLD_SEC
        }
        return prefs.getInt(KEY_HOLD_SEC, DEFAULT_HOLD_SEC)
    }

    fun setPresenceHoldSeconds(context: Context, value: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_HOLD_SEC, value)
            .apply()
    }

    fun getHoldExtendNonUid(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_HOLD_EXTEND_NONUID, true)

    fun setHoldExtendNonUid(context: Context, value: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_HOLD_EXTEND_NONUID, value)
            .apply()
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
                val currentId = if (segments.size >= 3 && segments[0] == "whip" && segments[1] == "thinklet") {
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

                builder.encodedPath("/whip/thinklet/${currentId ?: deviceId}")

                if (!parsed.encodedQuery.isNullOrBlank()) builder.encodedQuery(parsed.encodedQuery)
                if (!parsed.fragment.isNullOrBlank()) builder.fragment(parsed.fragment)
                builder.build().toString()
            }
        } catch (_: Exception) {
            trimmed
        }
    }
}
