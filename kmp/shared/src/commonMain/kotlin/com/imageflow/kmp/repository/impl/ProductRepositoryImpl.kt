package com.imageflow.kmp.repository.impl

import com.imageflow.kmp.database.DatabaseProvider
import com.imageflow.kmp.models.Product
import com.imageflow.kmp.models.ProductStatus
import com.imageflow.kmp.repository.ProductRepository

class ProductRepositoryImpl : ProductRepository {
    private val db by lazy { DatabaseProvider.create() }

    override suspend fun getProduct(id: String): Product? =
        db.productQueries.selectById(id).executeAsOneOrNull()?.let { row ->
            Product(
                id = row.id,
                model = row.model,
                serialNumber = row.serial_number,
                sequenceNumber = row.sequence_number?.toLong(),
                status = runCatching { ProductStatus.valueOf(row.status) }.getOrDefault(ProductStatus.ACTIVE)
            )
        }

    override suspend fun search(model: String?, serialNumber: String?, sequenceNumber: Long?): List<Product> {
        // Simple strategy: selectAll then filter in-memory (can be optimized with parameterized queries later)
        return db.productQueries.selectAll().executeAsList().map { row ->
            Product(
                id = row.id,
                model = row.model,
                serialNumber = row.serial_number,
                sequenceNumber = row.sequence_number?.toLong(),
                status = runCatching { ProductStatus.valueOf(row.status) }.getOrDefault(ProductStatus.ACTIVE)
            )
        }.filter { p ->
            (model == null || p.model == model) &&
            (serialNumber == null || p.serialNumber == serialNumber) &&
            (sequenceNumber == null || p.sequenceNumber == sequenceNumber)
        }
    }
}

