package com.imageflow.kmp.platform

actual interface Notifier {
    actual fun notify(title: String, message: String)
}

