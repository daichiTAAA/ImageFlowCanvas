package com.imageflow.kmp.repository

import com.imageflow.kmp.models.Product

interface ProductRepository {
    suspend fun getProduct(id: String): Product?
    suspend fun search(
        model: String? = null,
        serialNumber: String? = null,
        sequenceNumber: Long? = null,
    ): List<Product>
}

