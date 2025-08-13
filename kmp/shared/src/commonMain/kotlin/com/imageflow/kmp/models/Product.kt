package com.imageflow.kmp.models

// Based on docs 0313 6.3.1 and 0310 common model
data class Product(
    val id: String,
    val model: String,
    val serialNumber: String,
    val sequenceNumber: Long? = null,
    val status: ProductStatus = ProductStatus.ACTIVE,
)

