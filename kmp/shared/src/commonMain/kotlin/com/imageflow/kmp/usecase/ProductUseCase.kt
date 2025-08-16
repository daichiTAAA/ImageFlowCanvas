package com.imageflow.kmp.usecase

import com.imageflow.kmp.models.*
import com.imageflow.kmp.qr.BarcodeDecoder
import com.imageflow.kmp.qr.toProductInfo
import com.imageflow.kmp.repository.ProductRepository
import com.imageflow.kmp.network.ProductApiService
import com.imageflow.kmp.network.ApiResult
import com.imageflow.kmp.network.ProductSearchResponse
import com.imageflow.kmp.network.ProductSuggestion
import com.imageflow.kmp.workflow.ProductSearchQuery
import com.imageflow.kmp.workflow.ProductSearchResult

// Use case for QR code scanning and product identification based on F-021-1 requirements
class ScanProductUseCase(
    private val productRepository: ProductRepository,
    private val productApiService: ProductApiService,
    private val barcodeDecoder: BarcodeDecoder
) {
    
    suspend fun scanQrCode(rawData: String): QrScanResult {
        try {
            // Decode QR data
            val decodedInfo = barcodeDecoder.decode(rawData)
            val validationResult = barcodeDecoder.validate(decodedInfo)
            
            if (!validationResult.isValid) {
                return QrScanResult(
                    success = false,
                    productInfo = null,
                    rawData = rawData,
                    scanType = ScanType.QR_CODE,
                    confidence = 0f,
                    validationStatus = ValidationStatus.INVALID,
                    errorMessage = validationResult.errors.firstOrNull()?.message ?: "QRコードの形式が正しくありません"
                )
            }
            
            // Convert to ProductInfo
            val productInfo = decodedInfo.toProductInfo()
            if (productInfo == null) {
                return QrScanResult(
                    success = false,
                    productInfo = null,
                    rawData = rawData,
                    scanType = ScanType.QR_CODE,
                    confidence = 0f,
                    validationStatus = ValidationStatus.INVALID,
                    errorMessage = "必須項目が不足しています"
                )
            }
            
            // Try to find product locally first
            val localProduct = findProductLocally(productInfo)
            if (localProduct != null) {
                // Update access info for local product
                productRepository.updateAccessInfo(localProduct.id)
                
                return QrScanResult(
                    success = true,
                    productInfo = localProduct,
                    rawData = rawData,
                    scanType = ScanType.QR_CODE,
                    confidence = 1.0f,
                    validationStatus = ValidationStatus.VALID
                )
            }
            
            // Try to fetch from server
            val serverResult = fetchProductFromServer(productInfo)
            return when (serverResult) {
                is ApiResult.Success -> {
                    // Save to local cache
                    productRepository.saveProduct(serverResult.data)
                    
                    QrScanResult(
                        success = true,
                        productInfo = serverResult.data,
                        rawData = rawData,
                        scanType = ScanType.QR_CODE,
                        confidence = 0.9f,
                        validationStatus = ValidationStatus.VALID
                    )
                }
                is ApiResult.Error -> {
                    QrScanResult(
                        success = false,
                        productInfo = productInfo,
                        rawData = rawData,
                        scanType = ScanType.QR_CODE,
                        confidence = 0.5f,
                        validationStatus = ValidationStatus.NOT_FOUND,
                        errorMessage = "順序情報が見つかりませんでした: ${serverResult.message}"
                    )
                }
                is ApiResult.NetworkError -> {
                    // Allow offline operation with partial data
                    QrScanResult(
                        success = true,
                        productInfo = productInfo.copy(serverSyncStatus = SyncStatus.PENDING),
                        rawData = rawData,
                        scanType = ScanType.QR_CODE,
                        confidence = 0.7f,
                        validationStatus = ValidationStatus.VALID,
                        errorMessage = "オフラインモード: サーバー確認ができませんでした"
                    )
                }
            }
        } catch (e: Exception) {
            return QrScanResult(
                success = false,
                productInfo = null,
                rawData = rawData,
                scanType = ScanType.QR_CODE,
                confidence = 0f,
                validationStatus = ValidationStatus.INVALID,
                errorMessage = "QRコード処理エラー: ${e.message}"
            )
        }
    }
    
    private suspend fun findProductLocally(productInfo: ProductInfo): ProductInfo? {
        // Try multiple lookup strategies
        return productRepository.getProduct(productInfo.id)
            ?: productRepository.getProductByWorkOrderId(productInfo.workOrderId)
            ?: productRepository.getProductByQrData(productInfo.qrRawData ?: "")
    }
    
    private suspend fun fetchProductFromServer(productInfo: ProductInfo): ApiResult<ProductInfo> {
        // Try different server lookup strategies
        return productApiService.getProductByWorkOrderId(productInfo.workOrderId).let { result ->
            if (result is ApiResult.Success) {
                result
            } else {
                productApiService.getProductInfo(productInfo.id)
            }
        }
    }
}

// Use case for product search based on F-021-2 requirements
class SearchProductUseCase(
    private val productRepository: ProductRepository,
    private val productApiService: ProductApiService
) {
    
    suspend fun getProductById(productId: String): ApiResult<ProductInfo> {
        return productApiService.getProductInfo(productId)
    }
    
    suspend fun searchProducts(query: String, useServerSearch: Boolean = true): ProductSearchResult {
        val startTime = System.currentTimeMillis()
        
        try {
            // First search locally
            val localResults = searchLocally(query)
            
            if (!useServerSearch || localResults.isNotEmpty()) {
                return ProductSearchResult(
                    products = localResults,
                    totalCount = localResults.size,
                    query = createSearchQuery(query),
                    searchTimeMs = System.currentTimeMillis() - startTime
                )
            }
            
            // Search on server if local search yields no results
            val serverResult = searchOnServer(query)
            return when (serverResult) {
                is ApiResult.Success -> {
                    // Cache server results locally
                    serverResult.data.products.forEach { product ->
                        productRepository.saveProduct(product)
                    }
                    
                    ProductSearchResult(
                        products = serverResult.data.products,
                        totalCount = serverResult.data.totalCount,
                        query = createSearchQuery(query),
                        searchTimeMs = System.currentTimeMillis() - startTime
                    )
                }
                is ApiResult.Error -> {
                    ProductSearchResult(
                        products = localResults,
                        totalCount = localResults.size,
                        query = createSearchQuery(query),
                        searchTimeMs = System.currentTimeMillis() - startTime
                    )
                }
                is ApiResult.NetworkError -> {
                    ProductSearchResult(
                        products = localResults,
                        totalCount = localResults.size,
                        query = createSearchQuery(query),
                        searchTimeMs = System.currentTimeMillis() - startTime
                    )
                }
            }
        } catch (e: Exception) {
            return ProductSearchResult(
                products = emptyList(),
                totalCount = 0,
                query = createSearchQuery(query),
                searchTimeMs = System.currentTimeMillis() - startTime
            )
        }
    }
    
    // Overload: structured search by fields (productCode, machineNumber, etc.)
    suspend fun searchProducts(query: ProductSearchQuery, useServerSearch: Boolean = true): ProductSearchResult {
        val startTime = System.currentTimeMillis()
        
        return try {
            val localResults = productRepository.searchProducts(query)
            if (!useServerSearch || localResults.isNotEmpty()) {
                ProductSearchResult(
                    products = localResults,
                    totalCount = localResults.size,
                    query = query,
                    searchTimeMs = System.currentTimeMillis() - startTime
                )
            } else {
                when (val serverResult = productApiService.searchProducts(query)) {
                    is ApiResult.Success -> {
                        serverResult.data.products.forEach { productRepository.saveProduct(it) }
                        ProductSearchResult(
                            products = serverResult.data.products,
                            totalCount = serverResult.data.totalCount,
                            query = query,
                            searchTimeMs = System.currentTimeMillis() - startTime
                        )
                    }
                    is ApiResult.Error, is ApiResult.NetworkError -> {
                        ProductSearchResult(
                            products = localResults,
                            totalCount = localResults.size,
                            query = query,
                            searchTimeMs = System.currentTimeMillis() - startTime
                        )
                    }
                }
            }
        } catch (_: Exception) {
            ProductSearchResult(
                products = emptyList(),
                totalCount = 0,
                query = query,
                searchTimeMs = System.currentTimeMillis() - startTime
            )
        }
    }
    
    suspend fun getProductSuggestions(partialQuery: String): List<ProductSuggestion> {
        return try {
            when (val result = productApiService.getProductSuggestions(partialQuery)) {
                is ApiResult.Success -> result.data
                else -> {
                    // Fallback to local suggestions
                    val localProducts = productRepository.searchProducts(createSearchQuery(partialQuery))
                    localProducts.take(10).map { product ->
                        ProductSuggestion(
                            productId = product.id,
                            displayText = "${product.productCode} - ${product.machineNumber}",
                            productCode = product.productCode,
                            machineNumber = product.machineNumber,
                            relevanceScore = 0.8f
                        )
                    }
                }
            }
        } catch (e: Exception) {
            emptyList()
        }
    }
    
    private suspend fun searchLocally(query: String): List<ProductInfo> {
        return productRepository.searchProducts(createSearchQuery(query))
    }
    
    private suspend fun searchOnServer(query: String): ApiResult<ProductSearchResponse> {
        return productApiService.searchProducts(createSearchQuery(query))
    }
    
    private fun createSearchQuery(query: String): ProductSearchQuery {
        return ProductSearchQuery(
            workOrderId = if (query.startsWith("WORK")) query else null,
            instructionId = if (query.startsWith("INST")) query else null,
            productCode = if (!query.startsWith("WORK") && !query.startsWith("INST")) query else null,
            machineNumber = if (query.startsWith("MACHINE")) query else null,
            limit = 50
        )
    }
}
