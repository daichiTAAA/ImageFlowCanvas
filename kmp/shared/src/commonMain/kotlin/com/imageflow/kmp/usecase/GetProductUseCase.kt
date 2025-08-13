package com.imageflow.kmp.usecase

import com.imageflow.kmp.models.ProductInfo
import com.imageflow.kmp.repository.ProductRepository

class GetProductUseCase(private val repo: ProductRepository) {
    suspend operator fun invoke(id: String): ProductInfo? = repo.getProduct(id)
}
