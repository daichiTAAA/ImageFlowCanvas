package com.imageflow.kmp.di

import com.imageflow.kmp.repository.ProductRepository
import com.imageflow.kmp.repository.InspectionRepository
import com.imageflow.kmp.repository.impl.ProductRepositoryImpl
import com.imageflow.kmp.repository.impl.InspectionRepositoryImpl
import com.imageflow.kmp.network.ProductApiService
import com.imageflow.kmp.network.InspectionApiService
import com.imageflow.kmp.network.ktor.BasicRestClient
import com.imageflow.kmp.network.ktor.createHttpClient
import com.imageflow.kmp.network.impl.KtorProductApiService
import com.imageflow.kmp.network.impl.KtorInspectionApiService
import com.imageflow.kmp.qr.BarcodeDecoder
import com.imageflow.kmp.qr.DefaultBarcodeDecoder
import com.imageflow.kmp.usecase.*
import com.imageflow.kmp.ui.viewmodel.MobileInspectionViewModel
import kotlinx.coroutines.CoroutineScope
import com.imageflow.kmp.settings.AppSettings
import com.imageflow.kmp.platform.PlatformDefaults

// Simple dependency injection container for the KMP application
object DependencyContainer {
    
    // Repository instances
    private val productRepository: ProductRepository by lazy { ProductRepositoryImpl() }
    private val inspectionRepository: InspectionRepository by lazy { InspectionRepositoryImpl() }
    
    // Network clients and services
    private var apiBaseUrl: String = AppSettings.getBaseUrl() ?: PlatformDefaults.defaultApiBase()
    private var processCode: String = AppSettings.getProcessCode() ?: "DEFAULT"
    private var authToken: String? = AppSettings.getAuthToken()
    private val httpClient by lazy { createHttpClient() }
    // Rest client uses dynamic base supplier so changes reflect immediately
    private val restClient by lazy { BasicRestClient(httpClient) { apiBaseUrl } }
    private val authApiService: com.imageflow.kmp.network.AuthApiService by lazy { com.imageflow.kmp.network.impl.KtorAuthApiService(restClient) }
    private val productApiService: ProductApiService by lazy { KtorProductApiService(restClient) }
    private val inspectionApiService: InspectionApiService by lazy { KtorInspectionApiService(restClient) }
    
    // QR decoder
    private val barcodeDecoder: BarcodeDecoder by lazy { DefaultBarcodeDecoder() }
    
    // Use case instances
    private val scanProductUseCase: ScanProductUseCase by lazy {
        ScanProductUseCase(productRepository, productApiService, barcodeDecoder)
    }
    
    private val searchProductUseCase: SearchProductUseCase by lazy {
        SearchProductUseCase(productRepository, productApiService)
    }
    
    private val inspectionWorkflowUseCase: InspectionWorkflowUseCase by lazy {
        InspectionWorkflowUseCase(inspectionRepository, productRepository, inspectionApiService)
    }
    
    private val syncUseCase: SyncUseCase by lazy {
        SyncUseCase(inspectionRepository, inspectionApiService)
    }
    
    // Factory methods
    fun createMobileInspectionViewModel(viewModelScope: CoroutineScope): MobileInspectionViewModel {
        return MobileInspectionViewModel(
            scanProductUseCase = scanProductUseCase,
            searchProductUseCase = searchProductUseCase,
            inspectionWorkflowUseCase = inspectionWorkflowUseCase,
            syncUseCase = syncUseCase,
            viewModelScope = viewModelScope
        )
    }
    
    fun provideProductRepository(): ProductRepository = productRepository
    fun provideInspectionRepository(): InspectionRepository = inspectionRepository
    fun provideScanProductUseCase(): ScanProductUseCase = scanProductUseCase
    fun provideSearchProductUseCase(): SearchProductUseCase = searchProductUseCase
    fun provideInspectionWorkflowUseCase(): InspectionWorkflowUseCase = inspectionWorkflowUseCase
    fun provideProductApiService(): ProductApiService = productApiService
    fun provideInspectionApiService(): InspectionApiService = inspectionApiService
    fun provideRestClient(): com.imageflow.kmp.network.RestClient = restClient
    fun provideAuthApiService(): com.imageflow.kmp.network.AuthApiService = authApiService

    // Configuration hook for overriding API base URL at runtime
    fun configureApiBase(url: String) {
        apiBaseUrl = url
        // persist for next launch where supported
        try { AppSettings.setBaseUrl(url) } catch (_: Exception) { }
    }

    fun currentApiBase(): String = apiBaseUrl

    // Process code configuration
    fun configureProcessCode(code: String) {
        processCode = code
        try { AppSettings.setProcessCode(code) } catch (_: Exception) { }
    }
    fun currentProcessCode(): String = processCode

    // Auth token configuration
    fun configureAuthToken(token: String?) {
        authToken = token
        try { AppSettings.setAuthToken(token) } catch (_: Exception) { }
    }
    fun currentAuthToken(): String? = authToken
}

// Note: mock implementations were removed in favor of real Ktor-based services.
