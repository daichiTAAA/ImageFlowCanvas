package com.imageflow.kmp.ui.viewmodel

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import com.imageflow.kmp.di.DependencyContainer
import com.imageflow.kmp.network.ProductApiService
import com.imageflow.kmp.network.ApiResult
import com.imageflow.kmp.platform.PlatformDefaults
import com.imageflow.kmp.util.UrlUtils

data class ConnectionTestResult(val ok: Boolean, val message: String? = null)

class SettingsViewModel {
    private val _baseUrl = MutableStateFlow(DependencyContainer.currentApiBase())
    val baseUrl: StateFlow<String> = _baseUrl.asStateFlow()
    private val api: ProductApiService = DependencyContainer.provideProductApiService()
    private val _validationError = MutableStateFlow<String?>(null)
    val validationError: StateFlow<String?> = _validationError.asStateFlow()

    fun setBaseUrl(value: String) {
        _baseUrl.value = value
        // validate on change
        val (_, err) = UrlUtils.validateAndNormalizeBaseUrl(value)
        _validationError.value = err
    }

    fun apply() {
        val (normalized, err) = UrlUtils.validateAndNormalizeBaseUrl(_baseUrl.value)
        _validationError.value = err
        if (err == null && normalized != null) {
            _baseUrl.value = normalized
            DependencyContainer.configureApiBase(normalized)
        }
    }

    suspend fun testConnection(): ConnectionTestResult = when (val r = api.getProductsByType("")) {
        is ApiResult.Success -> ConnectionTestResult(true, null)
        is ApiResult.Error -> ConnectionTestResult(false, r.message)
        is ApiResult.NetworkError -> ConnectionTestResult(false, r.message)
    }

    fun resetToDefault() {
        val def = PlatformDefaults.defaultApiBase()
        _baseUrl.value = def
        _validationError.value = null
        DependencyContainer.configureApiBase(def)
    }
}
