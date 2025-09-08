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
        val autoResume = if (intent.hasExtra(EXTRA_AUTO_RESUME)) intent.getBooleanExtra(EXTRA_AUTO_RESUME, true) else null
        // BLE beacon extras (all optional)
        val beaconType = intent.getStringExtra(EXTRA_BEACON_TYPE)
        val eddystoneNs = intent.getStringExtra(EXTRA_EDDYSTONE_NAMESPACE)
        val eddystoneInst = intent.getStringExtra(EXTRA_EDDYSTONE_INSTANCE)
        val ibeaconUuid = intent.getStringExtra(EXTRA_IBEACON_UUID)
        val ibeaconMajor = if (intent.hasExtra(EXTRA_IBEACON_MAJOR)) intent.getIntExtra(EXTRA_IBEACON_MAJOR, 0) else null
        val ibeaconMinor = if (intent.hasExtra(EXTRA_IBEACON_MINOR)) intent.getIntExtra(EXTRA_IBEACON_MINOR, 0) else null
        val enterRssi = if (intent.hasExtra(EXTRA_ENTER_RSSI)) intent.getIntExtra(EXTRA_ENTER_RSSI, -70) else null
        val exitRssi = if (intent.hasExtra(EXTRA_EXIT_RSSI)) intent.getIntExtra(EXTRA_EXIT_RSSI, -80) else null
        val enterSec = if (intent.hasExtra(EXTRA_ENTER_SEC)) intent.getIntExtra(EXTRA_ENTER_SEC, 2) else null
        val exitSec = if (intent.hasExtra(EXTRA_EXIT_SEC)) intent.getIntExtra(EXTRA_EXIT_SEC, 5) else null
        if (!url.isNullOrBlank()) {
            AppConfig.setWhipUrl(context, url)
            Log.i(TAG, "Updated WHIP URL: $url")
        }
        if (auto != null) {
            AppConfig.setAutoStart(context, auto)
            Log.i(TAG, "Updated auto.start: $auto")
        }
        if (autoResume != null) {
            AppConfig.setAutoResume(context, autoResume)
            Log.i(TAG, "Updated auto.resume: $autoResume")
        }

        if (!beaconType.isNullOrBlank()) {
            AppConfig.setBeaconType(context, beaconType)
            Log.i(TAG, "Updated beacon.type: $beaconType")
        }
        if (!eddystoneNs.isNullOrBlank() || !eddystoneInst.isNullOrBlank()) {
            AppConfig.setEddystoneUid(context, eddystoneNs, eddystoneInst)
            Log.i(TAG, "Updated Eddystone UID: ns=${eddystoneNs} inst=${eddystoneInst}")
        }
        if (!ibeaconUuid.isNullOrBlank() || ibeaconMajor != null || ibeaconMinor != null) {
            AppConfig.setIBeacon(context, ibeaconUuid, ibeaconMajor, ibeaconMinor)
            Log.i(TAG, "Updated iBeacon: uuid=${ibeaconUuid} major=${ibeaconMajor} minor=${ibeaconMinor}")
        }
        if (enterRssi != null) { AppConfig.setEnterRssi(context, enterRssi); Log.i(TAG, "Updated privacy.enter.rssi: $enterRssi") }
        if (exitRssi != null) { AppConfig.setExitRssi(context, exitRssi); Log.i(TAG, "Updated privacy.exit.rssi: $exitRssi") }
        if (enterSec != null) { AppConfig.setEnterSeconds(context, enterSec); Log.i(TAG, "Updated privacy.enter.seconds: $enterSec") }
        if (exitSec != null) { AppConfig.setExitSeconds(context, exitSec); Log.i(TAG, "Updated privacy.exit.seconds: $exitSec") }
    }

    companion object {
        const val ACTION_SET_CONFIG = "com.imageflow.thinklet.SET_CONFIG"
        const val EXTRA_URL = "url"
        const val EXTRA_AUTO = "autoStart"
        const val EXTRA_AUTO_RESUME = "autoResume"
        const val EXTRA_BEACON_TYPE = "beacon.type" // "eddystone_uid" | "ibeacon" | "any"
        const val EXTRA_EDDYSTONE_NAMESPACE = "eddystone.namespace"
        const val EXTRA_EDDYSTONE_INSTANCE = "eddystone.instance"
        const val EXTRA_IBEACON_UUID = "ibeacon.uuid"
        const val EXTRA_IBEACON_MAJOR = "ibeacon.major"
        const val EXTRA_IBEACON_MINOR = "ibeacon.minor"
        const val EXTRA_ENTER_RSSI = "privacy.enter.rssi"
        const val EXTRA_EXIT_RSSI = "privacy.exit.rssi"
        const val EXTRA_ENTER_SEC = "privacy.enter.seconds"
        const val EXTRA_EXIT_SEC = "privacy.exit.seconds"
        private const val TAG = "ThinkletConfig"
    }
}
