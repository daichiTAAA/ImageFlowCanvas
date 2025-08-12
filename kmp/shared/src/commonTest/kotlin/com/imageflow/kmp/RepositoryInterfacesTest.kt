package com.imageflow.kmp

import com.imageflow.kmp.models.Product
import com.imageflow.kmp.repository.ProductRepository
import kotlin.test.Test
import kotlin.test.assertEquals

private class InMemoryProductRepo : ProductRepository {
    private val data = mutableMapOf<String, Product>()
    override suspend fun getProduct(id: String): Product? = data[id]
    override suspend fun search(model: String?, serialNumber: String?, sequenceNumber: Long?) =
        data.values.filter { p ->
            (model == null || p.model == model) &&
            (serialNumber == null || p.serialNumber == serialNumber) &&
            (sequenceNumber == null || p.sequenceNumber == sequenceNumber)
        }

    fun put(p: Product) { data[p.id] = p }
}

class RepositoryInterfacesTest {
    @Test
    fun product_repository_contract() = kotlinx.coroutines.test.runTest {
        val repo = InMemoryProductRepo()
        repo.put(Product(id = "1", model = "A", serialNumber = "S1"))
        assertEquals("A", repo.getProduct("1")?.model)
        assertEquals(1, repo.search(model = "A").size)
    }
}

