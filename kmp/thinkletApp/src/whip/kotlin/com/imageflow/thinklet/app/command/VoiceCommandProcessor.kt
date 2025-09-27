package com.imageflow.thinklet.app.command

import com.imageflow.thinklet.app.audio.RecognizedPhrase
import java.time.Instant
import java.util.Locale

class VoiceCommandProcessor(
    private val deviceNameProvider: () -> String,
    private val confidenceProvider: () -> Float,
) {
    fun evaluate(phrase: RecognizedPhrase): VoiceCommand? {
        val sanitized = phrase.text.replace(SPACED_WHITESPACE, " ").replace('\u3000', ' ').trim()
        if (sanitized.isEmpty()) return null

        val myDeviceName = deviceNameProvider().trim()
        val (deviceCandidate, commandPart) = splitDevicePrefix(sanitized, myDeviceName)
        val canonicalDevice = deviceCandidate?.let { canonicalDeviceName(it, myDeviceName) }
        val normalizedCommand = commandPart.replace(SPACED_WHITESPACE, "").trim()
        if (normalizedCommand.isEmpty()) return null

        val action = resolveAction(normalizedCommand) ?: return null

        val targetDevice = canonicalDevice ?: when {
            action.requiresDevice -> myDeviceName.ifBlank { null }
            else -> null
        }

        if (action.requiresDevice && targetDevice == null) {
            return null
        }

        val confidence = phrase.confidence
        if (phrase.isFinal && action.requiresHighConfidence && confidence < confidenceProvider()) {
            return null
        }

        return VoiceCommand(
            deviceName = targetDevice,
            action = action,
            rawText = phrase.text,
            normalizedText = normalizedCommand,
            confidence = confidence,
            timestamp = phrase.timestamp,
            provisional = !phrase.isFinal,
        )
    }

    private fun splitDevicePrefix(content: String, myDeviceName: String?): Pair<String?, String> {
        val tokens = content.split(' ', limit = 2)
        if (tokens.isEmpty()) return null to content
        val first = tokens[0]
        val canonical = canonicalDeviceName(first, myDeviceName)
        return if (canonical != null) {
            val remaining = if (tokens.size > 1) tokens[1] else content.removePrefix(first).trimStart()
            canonical to remaining
        } else {
            val candidate = myDeviceName?.takeIf { !it.isNullOrBlank() }
            if (!candidate.isNullOrBlank() && content.startsWith(candidate)) {
                val remaining = content.removePrefix(candidate).trimStart()
                candidate to remaining
            } else null to content
        }
    }

    private fun canonicalDeviceName(input: String, myDeviceName: String?): String? {
        val normalized = input.lowercase(Locale.JAPAN)
        DEVICE_ALIASES[normalized]?.let { return it }
        if (!myDeviceName.isNullOrBlank()) {
            val mine = myDeviceName.lowercase(Locale.JAPAN)
            if (normalized == mine) {
                return myDeviceName
            }
        }
        return null
    }

    private fun resolveAction(normalized: String): VoiceCommandAction? {
        return COMMAND_PATTERNS.entries.firstOrNull { entry ->
            entry.value.any { candidate -> normalized.contains(candidate) }
        }?.key
    }

    companion object {
        private val SPACED_WHITESPACE = Regex("\\s+")

        private val DEVICE_ALIASES = mapOf(
            "レッド" to "レッド",
            "れっど" to "レッド",
            "ブルー" to "ブルー",
            "ぶるー" to "ブルー",
            "イエロー" to "イエロー",
            "いえろー" to "イエロー",
            "グリーン" to "グリーン",
            "ぐりーん" to "グリーン",
            "パープル" to "パープル",
            "ホワイト" to "ホワイト",
            "ほわいと" to "ホワイト",
            "ブラック" to "ブラック",
            "ぶらっく" to "ブラック",
            "オレンジ" to "オレンジ",
            "おれんじ" to "オレンジ",
            "ピンク" to "ピンク",
            "ぴんく" to "ピンク",
            "ライム" to "ライム",
            "らいむ" to "ライム",
            "シアン" to "シアン",
            "しあん" to "シアン",
            "ターコイズ" to "ターコイズ",
            "たーこいず" to "ターコイズ",
            "ネイビー" to "ネイビー",
            "ねいびー" to "ネイビー",
            "コバルト" to "コバルト",
            "こばると" to "コバルト",
            "ラベンダー" to "ラベンダー",
            "らべんだー" to "ラベンダー",
            "コーラル" to "コーラル",
            "こーらる" to "コーラル",
            "アンバー" to "アンバー",
            "あんばー" to "アンバー",
            "アイス" to "アイス",
            "あいす" to "アイス",
            "サンド" to "サンド",
            "さんど" to "サンド",
            "モカ" to "モカ",
            "もか" to "モカ",
            "ミント" to "ミント",
            "みんと" to "ミント",
            "オリーブ" to "オリーブ",
            "おりーぶ" to "オリーブ",
            "プラム" to "プラム",
            "ぷらむ" to "プラム",
            "ティール" to "ティール",
            "てぃーる" to "ティール",
            "サファイア" to "サファイア",
            "さふぁいあ" to "サファイア",
            "エメラルド" to "エメラルド",
            "えめらるど" to "エメラルド",
            "トパーズ" to "トパーズ",
            "とぱーず" to "トパーズ",
            "ジェイド" to "ジェイド",
            "じぇいど" to "ジェイド",
            "バーガンディ" to "バーガンディ",
            "ばーがんでぃ" to "バーガンディ",
            "カナリア" to "カナリア",
            "かなりあ" to "カナリア",
            "スモーキー" to "スモーキー",
            "すもーきー" to "スモーキー",
            "グラファイト" to "グラファイト",
            "ぐらふぁいと" to "グラファイト",
            "クォーツ" to "クォーツ",
            "くぉーつ" to "クォーツ",
            "サクラ" to "サクラ",
            "さくら" to "サクラ",
            "サニー" to "サニー",
            "さにー" to "サニー",
            "ネオン" to "ネオン",
            "ねおん" to "ネオン",
            "ブライト" to "ブライト",
            "ぶらいと" to "ブライト",
            "ディープ" to "ディープ",
            "でぃーぷ" to "ディープ",
            "クリア" to "クリア",
            "くりあ" to "クリア",
            "ソフト" to "ソフト",
            "そふと" to "ソフト",
        )

        private val COMMAND_PATTERNS: Map<VoiceCommandAction, List<String>> = mapOf(
            VoiceCommandAction.RECORD_START to listOf("録画開始", "撮影開始", "録画スタート"),
            VoiceCommandAction.RECORD_STOP to listOf("録画停止", "撮影停止", "録画ストップ"),
            VoiceCommandAction.RECORD_PAUSE to listOf("録画一時停止", "録画ポーズ"),
            VoiceCommandAction.RECORD_RESUME to listOf("録画再開", "録画つづけ"),
            VoiceCommandAction.WORK_START to listOf("作業開始", "仕事開始", "開始します"),
            VoiceCommandAction.WORK_END to listOf("作業終了", "仕事終了", "終了します"),
            VoiceCommandAction.BREAK_START to listOf("休憩開始", "休憩入る"),
            VoiceCommandAction.BREAK_END to listOf("休憩終了", "休憩終わり", "休憩戻る"),
            VoiceCommandAction.STATUS_QUERY to listOf("状態は", "どうなってる", "ステータス", "今何してる"),
            VoiceCommandAction.DEVICE_NAME_QUERY to listOf("名前は", "デバイス名", "何色"),
            VoiceCommandAction.VOLUME_UP to listOf("音量上げ", "ボリューム上げ"),
            VoiceCommandAction.VOLUME_DOWN to listOf("音量下げ", "ボリューム下げ"),
            VoiceCommandAction.APP_EXIT to listOf("アプリ終了", "終了して"),
            VoiceCommandAction.CONNECTION_CHECK to listOf("接続確認", "つながってる"),
        )
    }
}

data class VoiceCommand(
    val deviceName: String?,
    val action: VoiceCommandAction,
    val rawText: String,
    val normalizedText: String,
    val confidence: Float,
    val timestamp: Instant,
    val provisional: Boolean,
)

enum class VoiceCommandAction(val requiresDevice: Boolean = true, val requiresHighConfidence: Boolean = true) {
    RECORD_START,
    RECORD_STOP,
    RECORD_PAUSE,
    RECORD_RESUME,
    WORK_START,
    WORK_END,
    BREAK_START,
    BREAK_END,
    STATUS_QUERY(requiresDevice = false, requiresHighConfidence = false),
    DEVICE_NAME_QUERY(requiresDevice = false, requiresHighConfidence = false),
    VOLUME_UP,
    VOLUME_DOWN,
    APP_EXIT,
    CONNECTION_CHECK;
}
