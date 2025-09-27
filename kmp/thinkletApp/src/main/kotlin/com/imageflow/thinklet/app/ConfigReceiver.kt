package com.imageflow.thinklet.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class ConfigReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_SET_CONFIG) return
        val url = intent.getStringExtra(EXTRA_URL)
        val autoStart = if (intent.hasExtra(EXTRA_AUTO)) intent.getBooleanExtra(EXTRA_AUTO, true) else null
        val autoResume = if (intent.hasExtra(EXTRA_AUTO_RESUME)) intent.getBooleanExtra(EXTRA_AUTO_RESUME, true) else null
        val backendUrl = intent.getStringExtra(EXTRA_BACKEND_URL)
        val deviceName = intent.getStringExtra(EXTRA_DEVICE_NAME)
        val confidence = if (intent.hasExtra(EXTRA_CONFIDENCE)) intent.getFloatExtra(EXTRA_CONFIDENCE, 0.8f) else null

        if (!url.isNullOrBlank()) {
            AppConfig.setWhipUrl(context, url)
            Log.i(TAG, "Updated WHIP URL: $url")
        }
        if (autoStart != null) {
            AppConfig.setAutoStart(context, autoStart)
            Log.i(TAG, "Updated auto.start: $autoStart")
        }
        if (autoResume != null) {
            AppConfig.setAutoResume(context, autoResume)
            Log.i(TAG, "Updated auto.resume: $autoResume")
        }
        if (!backendUrl.isNullOrBlank()) {
            AppConfig.setBackendUrl(context, backendUrl)
            Log.i(TAG, "Updated backend.url: $backendUrl")
        }
        if (!deviceName.isNullOrBlank()) {
            AppConfig.setDeviceName(context, deviceName)
            Log.i(TAG, "Updated device.name: $deviceName")
        }
        if (confidence != null) {
            AppConfig.setVoiceConfidenceThreshold(context, confidence)
            Log.i(TAG, "Updated voice.confidence: $confidence")
        }
    }

    companion object {
        const val ACTION_SET_CONFIG = "com.imageflow.thinklet.SET_CONFIG"
        const val EXTRA_URL = "url"
        const val EXTRA_AUTO = "autoStart"
        const val EXTRA_AUTO_RESUME = "autoResume"
        const val EXTRA_BACKEND_URL = "backendUrl"
        const val EXTRA_DEVICE_NAME = "deviceName"
        const val EXTRA_CONFIDENCE = "voiceConfidence"
        private const val TAG = "ThinkletConfig"
    }
}
