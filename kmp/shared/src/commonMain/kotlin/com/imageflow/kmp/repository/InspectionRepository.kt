package com.imageflow.kmp.repository

import com.imageflow.kmp.models.Inspection

interface InspectionRepository {
    suspend fun save(inspection: Inspection)
    suspend fun findByProduct(productId: String): List<Inspection>
    suspend fun unsynced(): List<Inspection>
}

