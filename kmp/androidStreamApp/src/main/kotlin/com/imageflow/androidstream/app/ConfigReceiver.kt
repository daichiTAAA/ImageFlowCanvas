package com.imageflow.androidstream.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.imageflow.androidstream.app.ble.BlePrivacyService

class ConfigReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_SET_CONFIG) return
        val url = intent.getStringExtra(EXTRA_URL)
        val autoStart = if (intent.hasExtra(EXTRA_AUTO)) intent.getBooleanExtra(EXTRA_AUTO, false) else null
        val autoResume = if (intent.hasExtra(EXTRA_AUTO_RESUME)) intent.getBooleanExtra(EXTRA_AUTO_RESUME, true) else null

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
        val matchStrict = if (intent.hasExtra(EXTRA_MATCH_STRICT)) intent.getBooleanExtra(EXTRA_MATCH_STRICT, true) else null
        val holdSec = if (intent.hasExtra(EXTRA_HOLD_SEC)) intent.getIntExtra(EXTRA_HOLD_SEC, 30) else null
        val holdExtend = if (intent.hasExtra(EXTRA_HOLD_EXTEND_NONUID)) intent.getBooleanExtra(EXTRA_HOLD_EXTEND_NONUID, true) else null

        if (!url.isNullOrBlank()) {
            AppConfig.setWhipUrl(context, url)
            Log.i(TAG, "Set WHIP URL: $url")
        }
        if (autoStart != null) {
            AppConfig.setAutoStart(context, autoStart)
            Log.i(TAG, "Set auto.start: $autoStart")
        }
        if (autoResume != null) {
            AppConfig.setAutoResume(context, autoResume)
            Log.i(TAG, "Set auto.resume: $autoResume")
        }

        if (!beaconType.isNullOrBlank()) {
            AppConfig.setBeaconType(context, beaconType)
            Log.i(TAG, "Set beacon.type: $beaconType")
        }
        if (!eddystoneNs.isNullOrBlank() || !eddystoneInst.isNullOrBlank()) {
            AppConfig.setEddystoneUid(context, eddystoneNs, eddystoneInst)
            Log.i(TAG, "Set Eddystone UID ns=${eddystoneNs} inst=${eddystoneInst}")
        }
        if (!ibeaconUuid.isNullOrBlank() || ibeaconMajor != null || ibeaconMinor != null) {
            AppConfig.setIBeacon(context, ibeaconUuid, ibeaconMajor, ibeaconMinor)
            Log.i(TAG, "Set iBeacon uuid=${ibeaconUuid} major=${ibeaconMajor} minor=${ibeaconMinor}")
        }
        if (enterRssi != null) AppConfig.setEnterRssi(context, enterRssi)
        if (exitRssi != null) AppConfig.setExitRssi(context, exitRssi)
        if (enterSec != null) AppConfig.setEnterSeconds(context, enterSec)
        if (exitSec != null) AppConfig.setExitSeconds(context, exitSec)
        if (matchStrict != null) AppConfig.setMatchStrict(context, matchStrict)
        if (holdSec != null) AppConfig.setPresenceHoldSeconds(context, holdSec)
        if (holdExtend != null) AppConfig.setHoldExtendNonUid(context, holdExtend)

        try {
            BlePrivacyService.start(context)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to start BLE service: ${e.message}")
        }
    }

    companion object {
        const val ACTION_SET_CONFIG = "com.imageflow.androidstream.SET_CONFIG"
        const val EXTRA_URL = "url"
        const val EXTRA_AUTO = "autoStart"
        const val EXTRA_AUTO_RESUME = "autoResume"
        const val EXTRA_BEACON_TYPE = "beacon.type"
        const val EXTRA_EDDYSTONE_NAMESPACE = "eddystone.namespace"
        const val EXTRA_EDDYSTONE_INSTANCE = "eddystone.instance"
        const val EXTRA_IBEACON_UUID = "ibeacon.uuid"
        const val EXTRA_IBEACON_MAJOR = "ibeacon.major"
        const val EXTRA_IBEACON_MINOR = "ibeacon.minor"
        const val EXTRA_ENTER_RSSI = "privacy.enter.rssi"
        const val EXTRA_EXIT_RSSI = "privacy.exit.rssi"
        const val EXTRA_ENTER_SEC = "privacy.enter.seconds"
        const val EXTRA_EXIT_SEC = "privacy.exit.seconds"
        const val EXTRA_MATCH_STRICT = "privacy.match.strict"
        const val EXTRA_HOLD_SEC = "privacy.hold.seconds"
        const val EXTRA_HOLD_EXTEND_NONUID = "privacy.hold.extendNonUid"

        private const val TAG = "AndroidStreamCfg"
    }
}
