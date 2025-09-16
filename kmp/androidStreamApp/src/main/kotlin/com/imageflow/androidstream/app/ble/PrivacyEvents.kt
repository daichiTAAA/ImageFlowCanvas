package com.imageflow.androidstream.app.ble

object PrivacyEvents {
    const val ACTION_PRIVACY_ENTER = "com.imageflow.androidstream.PRIVACY_ENTER"
    const val ACTION_PRIVACY_EXIT = "com.imageflow.androidstream.PRIVACY_EXIT"
    const val ACTION_PRIVACY_UPDATE = "com.imageflow.androidstream.PRIVACY_UPDATE"

    const val EXTRA_ZONE_ID = "zone_id"
    const val EXTRA_BEACON_ID = "beacon_id"
    const val EXTRA_RSSI = "rssi"
    const val EXTRA_PROXIMITY = "proximity"
    const val EXTRA_IN_PRIVACY = "in_privacy"
}
