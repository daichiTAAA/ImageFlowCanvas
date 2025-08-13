package com.imageflow.kmp.data.impl

import com.imageflow.kmp.data.SyncQueue
import com.imageflow.kmp.data.SyncTask
import com.imageflow.kmp.database.DatabaseProvider

class SqlSyncQueue(
    private val deviceId: String = "unknown-device",
    private val deviceType: String = "mobile",
    private val appVersion: String = "0.0.0",
) : SyncQueue {
    private val db by lazy { DatabaseProvider.create() }

    override fun enqueue(item: SyncTask) {
        // Minimal payload envelope; actual JSON schema is defined server-side
        val payload = "{" +
            "\"id\":\"${'$'}{item.id}\"" +
            "}"
        db.kmp_sync_queueQueries.insertItem(
            device_id = deviceId,
            device_type = deviceType,
            app_version = appVersion,
            entity_type = "generic",
            entity_id = item.id,
            operation = "INSERT",
            data = payload,
            priority = item.priority.toLong()
        )
    }
}

