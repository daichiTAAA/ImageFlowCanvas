package com.imageflow.thinklet.app.ble

object PrivacyEvents {
    const val ACTION_PRIVACY_ENTER = "com.imageflow.thinklet.PRIVACY_ENTER"
    const val ACTION_PRIVACY_EXIT = "com.imageflow.thinklet.PRIVACY_EXIT"
    const val ACTION_PRIVACY_UPDATE = "com.imageflow.thinklet.PRIVACY_UPDATE" // periodic RSSI/proximity updates

    // optional extras
    const val EXTRA_ZONE_ID = "zone_id"
    const val EXTRA_BEACON_ID = "beacon_id"
    const val EXTRA_RSSI = "rssi"
    const val EXTRA_PROXIMITY = "proximity" // "near" | "mid" | "far"
    const val EXTRA_IN_PRIVACY = "in_privacy" // boolean
}
