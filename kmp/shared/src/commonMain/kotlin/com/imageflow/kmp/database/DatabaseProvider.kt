package com.imageflow.kmp.database

import app.cash.sqldelight.db.SqlDriver
import com.imageflow.kmp.db.AppDatabase

expect object DriverFactory {
    fun createDriver(): SqlDriver
}

object DatabaseProvider {
    fun create(): AppDatabase = AppDatabase(DriverFactory.createDriver())
}

