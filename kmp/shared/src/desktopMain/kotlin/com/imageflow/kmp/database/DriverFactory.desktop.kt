package com.imageflow.kmp.database

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import com.imageflow.kmp.db.AppDatabase

actual object DriverFactory {
    actual fun createDriver(): SqlDriver {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        // Initialize schema for in-memory preview
        AppDatabase.Schema.create(driver)
        return driver
    }
}

