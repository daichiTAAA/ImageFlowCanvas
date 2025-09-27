package com.imageflow.thinklet.app.audio

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import java.time.Instant
import java.util.Locale

/**
 * Thin wrapper around [SpeechRecognizer] to provide continuous Japanese command recognition.
 * THINKLET SDK exposes richer audio primitives, but on developer hardware we fall back to
 * platform speech APIs while still enabling XFE front-end processing via native audio stack.
 */
class AudioService(
    private val context: Context,
    private val onPhrase: (RecognizedPhrase) -> Unit,
    private val onStatus: (String) -> Unit,
    private val onError: (String) -> Unit,
) : RecognitionListener {

    private val handler = Handler(Looper.getMainLooper())
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false
    private var shouldRestart = true

    init {
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            onError("Speech recognition not available on this device")
        } else {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
                setRecognitionListener(this@AudioService)
            }
        }
    }

    fun start() {
        if (speechRecognizer == null) return
        if (isListening) return
        shouldRestart = true
        handler.post { startInternal() }
    }

    fun stop() {
        shouldRestart = false
        speechRecognizer?.stopListening()
        isListening = false
    }

    fun release() {
        shouldRestart = false
        speechRecognizer?.setRecognitionListener(null)
        speechRecognizer?.destroy()
        speechRecognizer = null
        handler.removeCallbacksAndMessages(null)
    }

    private fun startInternal() {
        val recognizer = speechRecognizer ?: return
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.JAPAN.toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
        }
        try {
            recognizer.startListening(intent)
            isListening = true
            onStatus("音声認識を開始しました")
        } catch (e: Exception) {
            Log.e(TAG, "startListening failed", e)
            onError("音声認識の開始に失敗しました: ${e.message}")
        }
    }

    override fun onReadyForSpeech(params: Bundle?) {
        onStatus("音声認識待機中…")
    }

    override fun onBeginningOfSpeech() {
        onStatus("音声入力検出")
    }

    override fun onRmsChanged(rmsdB: Float) {
        // Could forward to visualizer in future releases
    }

    override fun onBufferReceived(buffer: ByteArray?) {
        // Raw audio available if we later combine with THINKLET SDK streaming APIs
    }

    override fun onEndOfSpeech() {
        onStatus("音声入力終了")
        isListening = false
    }

    override fun onError(error: Int) {
        val message = when (error) {
            SpeechRecognizer.ERROR_AUDIO -> "音声入力エラー"
            SpeechRecognizer.ERROR_CLIENT -> "クライアントエラー"
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "マイク権限がありません"
            SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "ネットワークエラー"
            SpeechRecognizer.ERROR_NO_MATCH -> "コマンドを認識できませんでした"
            SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "音声認識がビジー状態です"
            SpeechRecognizer.ERROR_SERVER -> "音声認識サーバーエラー"
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "音声入力が検出されませんでした"
            else -> "不明な音声エラー($error)"
        }
        onError(message)
        isListening = false
        if (shouldRestart) {
            handler.postDelayed({ startInternal() }, RESTART_DELAY_MS)
        }
    }

    override fun onResults(results: Bundle?) {
        handleResults(results, isFinal = true)
        isListening = false
        if (shouldRestart) {
            handler.postDelayed({ startInternal() }, RESTART_DELAY_MS)
        }
    }

    override fun onPartialResults(partialResults: Bundle?) {
        handleResults(partialResults, isFinal = false)
    }

    override fun onEvent(eventType: Int, params: Bundle?) {
        // no-op
    }

    private fun handleResults(bundle: Bundle?, isFinal: Boolean) {
        val recognitions = bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) ?: return
        val confidences = bundle.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES)
        recognitions.forEachIndexed { index, text ->
            val confidence = confidences?.getOrNull(index) ?: confidences?.firstOrNull() ?: DEFAULT_CONFIDENCE
            val phrase = RecognizedPhrase(
                text = text.trim(),
                confidence = confidence,
                timestamp = Instant.now(),
                isFinal = isFinal,
            )
            onPhrase(phrase)
        }
    }

    companion object {
        private const val TAG = "ThinkletAudioSvc"
        private const val RESTART_DELAY_MS = 400L
        private const val DEFAULT_CONFIDENCE = 0.5f
    }
}

data class RecognizedPhrase(
    val text: String,
    val confidence: Float,
    val timestamp: Instant,
    val isFinal: Boolean,
)
