package com.imageflow.kmp.repository.impl

import com.imageflow.kmp.database.DatabaseProvider
import com.imageflow.kmp.models.Inspection
import com.imageflow.kmp.repository.InspectionRepository

class InspectionRepositoryImpl : InspectionRepository {
    private val db by lazy { DatabaseProvider.create() }

    override suspend fun save(inspection: Inspection) {
        db.inspectionQueries.insertOrReplace(
            id = inspection.id,
            product_id = inspection.productId,
            result = inspection.result,
            timestamp = inspection.timestamp,
            synced = if (inspection.synced) 1 else 0
        )
    }

    override suspend fun findByProduct(productId: String): List<Inspection> =
        db.inspectionQueries.selectByProduct(productId).executeAsList().map { row ->
            Inspection(
                id = row.id,
                productId = row.product_id,
                result = row.result,
                timestamp = row.timestamp,
                synced = row.synced == 1
            )
        }

    override suspend fun unsynced(): List<Inspection> =
        db.inspectionQueries.selectUnsynced().executeAsList().map { row ->
            Inspection(
                id = row.id,
                productId = row.product_id,
                result = row.result,
                timestamp = row.timestamp,
                synced = row.synced == 1
            )
        }
}

