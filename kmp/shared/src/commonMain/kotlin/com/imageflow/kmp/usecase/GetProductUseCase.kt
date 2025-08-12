package com.imageflow.kmp.usecase

import com.imageflow.kmp.models.Product
import com.imageflow.kmp.repository.ProductRepository

class GetProductUseCase(private val repo: ProductRepository) {
    suspend operator fun invoke(id: String): Product? = repo.getProduct(id)
}

