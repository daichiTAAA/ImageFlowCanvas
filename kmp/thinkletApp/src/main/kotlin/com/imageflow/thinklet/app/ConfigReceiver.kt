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
    }

    companion object {
        const val ACTION_SET_CONFIG = "com.imageflow.thinklet.SET_CONFIG"
        const val EXTRA_URL = "url"
        const val EXTRA_AUTO = "autoStart"
        const val EXTRA_AUTO_RESUME = "autoResume"
        private const val TAG = "ThinkletConfig"
    }
}
