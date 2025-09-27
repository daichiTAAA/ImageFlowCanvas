package com.imageflow.thinklet.app

import android.content.Context
import android.net.Uri
import android.provider.Settings
import java.security.MessageDigest

object AppConfig {
    private const val PREFS = "thinklet_prefs"
    private const val KEY_URL = "whip.url"
    private const val KEY_AUTO = "auto.start"
    private const val KEY_AUTO_RESUME = "auto.resume"
    private const val KEY_BACKEND_URL = "backend.url"
    private const val KEY_DEVICE_NAME = "device.name"
    private const val KEY_CONFIDENCE = "voice.confidence"

    fun getWhipUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY_URL, null)
        if (!existing.isNullOrBlank()) {
            val sanitized = sanitizeWhipUrl(context, existing)
            if (sanitized != existing) {
                prefs.edit().putString(KEY_URL, sanitized).apply()
            }
            return sanitized
        }
        val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        return "http://192.168.0.5:8889/uplink/${deviceId}/whip"
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

    fun getBackendUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getString(KEY_BACKEND_URL, "http://192.168.0.5:8000")!!.trimEnd('/')
    }

    fun setBackendUrl(context: Context, url: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_BACKEND_URL, url.trim()).apply()
    }

    fun getDeviceName(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val stored = prefs.getString(KEY_DEVICE_NAME, null)
        if (!stored.isNullOrBlank()) return stored

        val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        val generated = generateColorName(deviceId ?: "")
        prefs.edit().putString(KEY_DEVICE_NAME, generated).apply()
        return generated
    }

    fun setDeviceName(context: Context, name: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_DEVICE_NAME, name.trim()).apply()
    }

    fun getVoiceConfidenceThreshold(context: Context): Float {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getFloat(KEY_CONFIDENCE, 0.8f)
    }

    fun setVoiceConfidenceThreshold(context: Context, threshold: Float) {
        val clamped = threshold.coerceIn(0.0f, 1.0f)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putFloat(KEY_CONFIDENCE, clamped).apply()
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
                val currentId = if (segments.size >= 3 && segments[0] == "uplink") {
                    segments[1].ifBlank { deviceId }
                } else {
                    slug?.ifBlank { null }
                }
                val builder = Uri.Builder().scheme(parsed.scheme)
                val authority = parsed.encodedAuthority ?: run {
                    val host = parsed.host ?: ""
                    val port = if (parsed.port != -1) ":${parsed.port}" else ""
                    host + port
                }
                if (authority.isNotBlank()) builder.encodedAuthority(authority)
                builder.encodedPath("/uplink/${currentId ?: deviceId}/whip")
                if (!parsed.encodedQuery.isNullOrBlank()) builder.encodedQuery(parsed.encodedQuery)
                if (!parsed.fragment.isNullOrBlank()) builder.fragment(parsed.fragment)
                builder.build().toString()
            }
        } catch (_: Exception) {
            trimmed
        }
    }

    private val toneWords = listOf(
        "ブライト",
        "クリア",
        "ソフト",
        "ディープ",
        "スカイ",
        "サニー",
        "ネオン",
        "フォレスト",
        "オーシャン",
        "アース",
        "ピュア",
        "フレッシュ",
        "スノー",
        "ナイト",
        "ミント",
        "サクラ",
    )

    private val baseWords = listOf(
        "レッド",
        "ブルー",
        "イエロー",
        "グリーン",
        "パープル",
        "ホワイト",
        "ブラック",
        "オレンジ",
        "ピンク",
        "ライム",
        "シアン",
        "ターコイズ",
        "ネイビー",
        "コバルト",
        "ラベンダー",
        "コーラル",
        "アンバー",
        "アイス",
        "サンド",
        "モカ",
        "オリーブ",
        "プラム",
        "ティール",
        "バーガンディ",
        "カナリア",
        "スモーキー",
        "サファイア",
        "エメラルド",
        "トパーズ",
        "グラファイト",
        "クォーツ",
        "ジェイド",
    )

    private val suffixWords = listOf(
        "ゼロ",
        "ワン",
        "ツー",
        "スリー",
        "フォー",
        "ファイブ",
        "シックス",
        "セブン",
        "エイト",
        "ナイン",
        "アルファ",
        "ベータ",
        "ガンマ",
        "デルタ",
        "シグマ",
        "オメガ",
    )

    private fun Byte.toIndex(mod: Int): Int = (toInt() and 0xFF) % mod

    private fun generateColorName(input: String): String {
        if (input.isBlank()) {
            return toneWords.first() + baseWords.first() + suffixWords.first()
        }
        val digest = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        val tone = toneWords[digest[0].toIndex(toneWords.size)]
        val base = baseWords[digest[1].toIndex(baseWords.size)]
        val suffix = suffixWords[digest[2].toIndex(suffixWords.size)]
        return tone + base + suffix
    }
}
