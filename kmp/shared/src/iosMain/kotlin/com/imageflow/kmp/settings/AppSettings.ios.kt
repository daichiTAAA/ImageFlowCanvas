package com.imageflow.kmp.settings

import platform.Foundation.NSUserDefaults

actual object AppSettings {
    private const val KEY_BASE_URL = "api_base_url"
    private const val KEY_CAMERA_ID = "selected_camera_id"
    private val defaults: NSUserDefaults = NSUserDefaults.standardUserDefaults()

    actual fun getBaseUrl(): String? = defaults.stringForKey(KEY_BASE_URL)

    actual fun setBaseUrl(url: String) {
        defaults.setObject(url, forKey = KEY_BASE_URL)
    }

    actual fun getSelectedCameraId(): String? = defaults.stringForKey(KEY_CAMERA_ID)
    actual fun setSelectedCameraId(id: String?) {
        if (id == null) defaults.removeObjectForKey(KEY_CAMERA_ID) else defaults.setObject(id, forKey = KEY_CAMERA_ID)
    }
}
