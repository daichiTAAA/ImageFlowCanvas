package com.imageflow.thinklet.app

import android.content.Context
import android.provider.Settings

object AppConfig {
    private const val PREFS = "thinklet_prefs"
    private const val KEY_URL = "whip.url"
    private const val KEY_AUTO = "auto.start"
    private const val KEY_AUTO_RESUME = "auto.resume" // resume WHIP automatically after privacy exit
    // BLE beacon filters and thresholds
    private const val KEY_BCN_TYPE = "beacon.type" // "eddystone_uid" | "ibeacon" | "any"
    private const val KEY_BCN_NS = "beacon.namespace" // Eddystone-UID namespace (hex 10 bytes)
    private const val KEY_BCN_INST = "beacon.instance" // Eddystone-UID instance (hex 6 bytes) optional
    private const val KEY_BCN_UUID = "beacon.uuid" // iBeacon UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
    private const val KEY_BCN_MAJOR = "beacon.major"
    private const val KEY_BCN_MINOR = "beacon.minor"
    private const val KEY_RSSI_ENTER = "privacy.enter.rssi" // default -70
    private const val KEY_RSSI_EXIT = "privacy.exit.rssi"   // default -80
    private const val KEY_ENTER_SEC = "privacy.enter.seconds" // default 2
    private const val KEY_EXIT_SEC = "privacy.exit.seconds"   // default 5
    private const val KEY_MATCH_STRICT = "privacy.match.strict" // only control by whitelisted beacons
    private const val KEY_HOLD_SEC = "privacy.hold.seconds" // presence hold to tolerate sparse adverts (default 30)
    private const val KEY_HOLD_EXTEND_NONUID = "privacy.hold.extendNonUid" // extend hold with non-UID frames from same MAC

    fun getWhipUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY_URL, null)
        if (!existing.isNullOrBlank()) return existing
        val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        return "http://192.168.0.5:8889/whip/thinklet/${deviceId}"
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

    fun getAutoResume(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getBoolean(KEY_AUTO_RESUME, true)
    }

    fun setAutoResume(context: Context, auto: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_AUTO_RESUME, auto).apply()
    }

    // ---- BLE beacon config accessors ----
    fun getBeaconType(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getString(KEY_BCN_TYPE, "any") ?: "any"
    }

    fun setBeaconType(context: Context, t: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_BCN_TYPE, t).apply()
    }

    fun setEddystoneUid(context: Context, namespaceHex: String?, instanceHex: String?) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_BCN_NS, namespaceHex)
            .putString(KEY_BCN_INST, instanceHex)
            .apply()
    }

    fun getEddystoneNamespace(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_BCN_NS, null)

    fun getEddystoneInstance(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_BCN_INST, null)

    fun setIBeacon(context: Context, uuid: String?, major: Int?, minor: Int?) {
        val e = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
        e.putString(KEY_BCN_UUID, uuid)
        if (major != null) e.putInt(KEY_BCN_MAJOR, major) else e.remove(KEY_BCN_MAJOR)
        if (minor != null) e.putInt(KEY_BCN_MINOR, minor) else e.remove(KEY_BCN_MINOR)
        e.apply()
    }

    fun getIBeaconUuid(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_BCN_UUID, null)

    fun getIBeaconMajor(context: Context): Int? =
        if (context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).contains(KEY_BCN_MAJOR))
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_BCN_MAJOR, 0) else null

    fun getIBeaconMinor(context: Context): Int? =
        if (context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).contains(KEY_BCN_MINOR))
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_BCN_MINOR, 0) else null

    fun getEnterRssi(context: Context): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_RSSI_ENTER, -70)

    fun setEnterRssi(context: Context, rssi: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putInt(KEY_RSSI_ENTER, rssi).apply()
    }

    fun getExitRssi(context: Context): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_RSSI_EXIT, -80)

    fun setExitRssi(context: Context, rssi: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putInt(KEY_RSSI_EXIT, rssi).apply()
    }

    fun getEnterSeconds(context: Context): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_ENTER_SEC, 2)

    fun setEnterSeconds(context: Context, sec: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putInt(KEY_ENTER_SEC, sec).apply()
    }

    fun getExitSeconds(context: Context): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_EXIT_SEC, 5)

    fun setExitSeconds(context: Context, sec: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putInt(KEY_EXIT_SEC, sec).apply()
    }

    fun isMatchStrict(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_MATCH_STRICT, true)

    fun setMatchStrict(context: Context, strict: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_MATCH_STRICT, strict).apply()
    }

    fun getPresenceHoldSeconds(context: Context): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY_HOLD_SEC, 30)

    fun setPresenceHoldSeconds(context: Context, sec: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putInt(KEY_HOLD_SEC, sec).apply()
    }

    fun getHoldExtendNonUid(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_HOLD_EXTEND_NONUID, true)

    fun setHoldExtendNonUid(context: Context, enable: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_HOLD_EXTEND_NONUID, enable).apply()
    }
}
