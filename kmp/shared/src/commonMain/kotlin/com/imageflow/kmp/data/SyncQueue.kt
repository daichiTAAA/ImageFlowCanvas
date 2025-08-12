package com.imageflow.kmp.data

// client_sync_queue placeholder with priority control
interface SyncQueue {
    fun enqueue(item: SyncTask)
}

data class SyncTask(val id: String, val priority: Int)

