package com.imageflow.kmp.settings

import platform.Foundation.NSUserDefaults

actual object AppSettings {
    private const val KEY_BASE_URL = "api_base_url"
    private val defaults: NSUserDefaults = NSUserDefaults.standardUserDefaults()

    actual fun getBaseUrl(): String? = defaults.stringForKey(KEY_BASE_URL)

    actual fun setBaseUrl(url: String) {
        defaults.setObject(url, forKey = KEY_BASE_URL)
    }
}

