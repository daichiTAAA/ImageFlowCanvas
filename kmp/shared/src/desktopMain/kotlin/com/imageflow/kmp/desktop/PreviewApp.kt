package com.imageflow.kmp.desktop

import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import com.imageflow.kmp.ui.placeholder.RootUI

// Simple desktop preview entry for RootUI
fun main() = application {
    Window(onCloseRequest = ::exitApplication, title = "ImageFlow KMP Preview") {
        RootUI()
    }
}

