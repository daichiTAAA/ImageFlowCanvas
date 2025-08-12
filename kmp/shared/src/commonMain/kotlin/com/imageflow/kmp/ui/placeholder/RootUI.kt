package com.imageflow.kmp.ui.placeholder

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import com.imageflow.kmp.platform.provideCameraController

// Minimal Composable aligned with docs 0313 6.1.1
@Composable
fun RootUI() {
    var started by remember { mutableStateOf(false) }
    val camera = remember { provideCameraController() }
    LaunchedEffect(Unit) {
        camera.start()
        started = true
    }
    // In a real app, show UI; here we just ensure the composable triggers camera start.
    if (!started) {
        // no-op placeholder
    }
}
