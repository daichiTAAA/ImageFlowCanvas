package com.imageflow.thinklet.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class ConfigReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_SET_CONFIG) return
        val url = intent.getStringExtra(EXTRA_URL)
        val auto = if (intent.hasExtra(EXTRA_AUTO)) intent.getBooleanExtra(EXTRA_AUTO, true) else null
        if (!url.isNullOrBlank()) {
            AppConfig.setWhipUrl(context, url)
            Log.i(TAG, "Updated WHIP URL: $url")
        }
        if (auto != null) {
            AppConfig.setAutoStart(context, auto)
            Log.i(TAG, "Updated auto.start: $auto")
        }
    }

    companion object {
        const val ACTION_SET_CONFIG = "com.imageflow.thinklet.SET_CONFIG"
        const val EXTRA_URL = "url"
        const val EXTRA_AUTO = "autoStart"
        private const val TAG = "ThinkletConfig"
    }
}

