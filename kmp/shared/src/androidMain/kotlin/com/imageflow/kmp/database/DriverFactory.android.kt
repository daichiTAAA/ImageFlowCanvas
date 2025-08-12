package com.imageflow.kmp.database

import android.content.Context
import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.android.AndroidSqliteDriver
import com.imageflow.kmp.db.AppDatabase

object AndroidDbContextHolder {
    @Volatile
    lateinit var context: Context
}

actual object DriverFactory {
    actual fun createDriver(): SqlDriver {
        val ctx = if (thisInitialized()) AndroidDbContextHolder.context else throw IllegalStateException(
            "AndroidDbContextHolder.context is not initialized. Call AndroidDbContextHolder.context = <appContext> early in app."
        )
        return AndroidSqliteDriver(AppDatabase.Schema, ctx, "imageflow_kmp.db")
    }

    private fun thisInitialized(): Boolean =
        try {
            @Suppress("UNREACHABLE_CODE")
            AndroidDbContextHolder.context != null
        } catch (_: UninitializedPropertyAccessException) {
            false
        }
}

