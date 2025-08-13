package com.imageflow.kmp.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.imageflow.kmp.database.AndroidDbContextHolder
import com.imageflow.kmp.ui.placeholder.RootUI

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Initialize DB context for SQLDelight drivers used by :shared
        AndroidDbContextHolder.context = applicationContext

        setContent {
            RootUI()
        }
    }
}

