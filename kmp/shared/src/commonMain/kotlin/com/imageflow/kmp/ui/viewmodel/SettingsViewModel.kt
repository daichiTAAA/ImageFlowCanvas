package com.imageflow.kmp.ui.viewmodel

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import com.imageflow.kmp.di.DependencyContainer
import com.imageflow.kmp.network.ProductApiService
import com.imageflow.kmp.network.ApiResult
import com.imageflow.kmp.network.PlatformNetworkDiagnostics
import com.imageflow.kmp.platform.PlatformDefaults
import com.imageflow.kmp.util.UrlUtils
import com.imageflow.kmp.util.NetworkDebugUtils
import com.imageflow.kmp.util.ConnectionTroubleshootingGuide
import com.imageflow.kmp.network.RestClient

data class ConnectionTestResult(val ok: Boolean, val message: String? = null)
data class NetworkDiagnosisResult(
    val normalizedBase: String,
    val testPath: String,
    val finalUrl: String,
    val ok: Boolean,
    val message: String? = null,
    val troubleshootingGuide: String? = null,
)

class SettingsViewModel {
    private val _baseUrl = MutableStateFlow(DependencyContainer.currentApiBase())
    val baseUrl: StateFlow<String> = _baseUrl.asStateFlow()
    private val _authToken = MutableStateFlow(DependencyContainer.currentAuthToken())
    val authToken: StateFlow<String?> = _authToken.asStateFlow()
    private val _processCode = MutableStateFlow(DependencyContainer.currentProcessCode())
    val processCode: StateFlow<String> = _processCode.asStateFlow()
    private val api: ProductApiService = DependencyContainer.provideProductApiService()
    private val rest: RestClient = DependencyContainer.provideRestClient()
    private val _validationError = MutableStateFlow<String?>(null)
    val validationError: StateFlow<String?> = _validationError.asStateFlow()
    private val _processes = MutableStateFlow<List<com.imageflow.kmp.network.ProcessMasterKmp>>(emptyList())
    val processes: StateFlow<List<com.imageflow.kmp.network.ProcessMasterKmp>> = _processes.asStateFlow()

    fun setBaseUrl(value: String) {
        _baseUrl.value = value
        // validate on change
        val (_, err) = UrlUtils.validateAndNormalizeBaseUrl(value)
        _validationError.value = err
    }

    fun apply() {
        val previous = DependencyContainer.currentApiBase()
        val (normalized, err) = UrlUtils.validateAndNormalizeBaseUrl(_baseUrl.value)
        _validationError.value = err
        if (err == null && normalized != null) {
            _baseUrl.value = normalized
            DependencyContainer.configureApiBase(normalized)
            // If base URL changed, clear token to avoid cross-origin token mismatch
            if (previous.trimEnd('/') != normalized.trimEnd('/')) {
                DependencyContainer.configureAuthToken(null)
                _authToken.value = null
                // Also clear cached processes; require re-login and reload
                try { (this as? Any)?.let { } } catch (_: Exception) { }
            }
        }
        // Apply process code immediately as well
        if (_processCode.value.isNotBlank()) {
            DependencyContainer.configureProcessCode(_processCode.value.trim())
        }
    }

    fun setProcessCode(value: String) {
        _processCode.value = value
    }

    suspend fun login(username: String, password: String): Boolean {
        val auth = DependencyContainer.provideAuthApiService()
        return when (val res = auth.login(username, password)) {
            is ApiResult.Success -> {
                val token = res.data.access_token
                DependencyContainer.configureAuthToken(token)
                _authToken.value = token
                // Save credentials for auto re-login (for dev convenience)
                DependencyContainer.configureAuthCredentials(username, password)
                // Prefetch processes so dropdown has data immediately after login
                runCatching { loadProcesses() }
                true
            }
            is ApiResult.Error -> { _validationError.value = res.message; false }
            is ApiResult.NetworkError -> { _validationError.value = res.message; false }
        }
    }

    fun logout() {
        DependencyContainer.configureAuthToken(null)
        _authToken.value = null
    }

    suspend fun loadProcesses() {
        // Ensure token is valid; if not, try auto re-login using stored credentials
        ensureValidToken()
        val api = DependencyContainer.provideInspectionApiService()
        when (val res = api.listProcesses(pageSize = 200)) {
            is ApiResult.Success -> _processes.value = res.data.items
            is ApiResult.Error -> {
                // no-op
            }
            is ApiResult.NetworkError -> {
                val msg = res.message?.lowercase() ?: ""
                if (msg.contains("401") || msg.contains("unauthorized")) {
                    // Token likely expired/invalid -> clear and notify
                    DependencyContainer.configureAuthToken(null)
                    _authToken.value = null
                    _validationError.value = "認証の有効期限が切れました。再度ログインしてください。"
                }
            }
        }
    }

    private suspend fun ensureValidToken() {
        val token = DependencyContainer.currentAuthToken()
        if (token.isNullOrBlank()) return
        val authApi = DependencyContainer.provideAuthApiService()
        when (authApi.me()) {
            is ApiResult.Success -> return
            is ApiResult.Error, is ApiResult.NetworkError -> {
                // Try auto re-login if we have stored credentials
                val (u, p) = DependencyContainer.currentAuthCredentials()
                if (!u.isNullOrBlank() && !p.isNullOrBlank()) {
                    val ok = login(u, p)
                    if (!ok) {
                        DependencyContainer.configureAuthToken(null)
                        _authToken.value = null
                    }
                } else {
                    DependencyContainer.configureAuthToken(null)
                    _authToken.value = null
                }
            }
        }
    }

    // Public wrapper to validate/refresh token before sensitive operations (e.g., streaming)
    suspend fun ensureTokenValidForStreaming(): Boolean {
        ensureValidToken()
        return !DependencyContainer.currentAuthToken().isNullOrBlank()
    }

    suspend fun testConnection(): ConnectionTestResult = when (val r = api.getProductsByCode("")) {
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

    suspend fun diagnose(tempUrl: String): NetworkDiagnosisResult {
        // Clear proxy settings before diagnosis
        NetworkDebugUtils.clearProxySettings()
        
        // Print network environment info for debugging
        println(NetworkDebugUtils.getNetworkEnvironmentInfo())
        
        // Validate URL structure
        val urlIssues = NetworkDebugUtils.validateUrl(tempUrl)
        if (urlIssues.isNotEmpty()) {
            println("SettingsViewModel: URL validation issues: ${urlIssues.joinToString(", ")}")
        }
        
        val (normalized, err) = UrlUtils.validateAndNormalizeBaseUrl(tempUrl)
        if (err != null || normalized == null) {
            return NetworkDiagnosisResult(
                normalizedBase = tempUrl,
                testPath = "/products",
                finalUrl = tempUrl,
                ok = false,
                message = err ?: "Invalid URL",
            )
        }
        val prev = DependencyContainer.currentApiBase()
        try {
            DependencyContainer.configureApiBase(normalized)
            val base = DependencyContainer.currentApiBase().trimEnd('/')
            val finalUrl = "$base/products"
            
            println("SettingsViewModel: Starting network diagnosis")
            println("SettingsViewModel: Original URL: $tempUrl")
            println("SettingsViewModel: Normalized base: $base")
            println("SettingsViewModel: Final URL: $finalUrl")
            
            return try {
                val startTime = System.currentTimeMillis()
                val response = rest.get("products")
                val duration = System.currentTimeMillis() - startTime
                
                println("SettingsViewModel: Connection successful in ${duration}ms")
                println("SettingsViewModel: Response length: ${response.length}")
                
                NetworkDiagnosisResult(
                    normalizedBase = base,
                    testPath = "/products",
                    finalUrl = finalUrl,
                    ok = true,
                    message = "Success (${duration}ms, ${response.length} chars)",
                    troubleshootingGuide = null,
                )
            } catch (e: Throwable) {
                println("SettingsViewModel: Connection failed: ${e.message}")
                println("SettingsViewModel: Exception type: ${e::class.simpleName}")
                e.printStackTrace()
                
                // Extract more specific error information
                val errorMessage = when {
                    e.message?.contains("localhost") == true || e.message?.contains("127.0.0.1") == true -> 
                        "Connection redirected to localhost:80 - possible proxy interference. Original error: ${e.message}"
                    e.message?.contains("Connection refused") == true -> 
                        "Connection refused - server may be down or unreachable at $finalUrl"
                    e.message?.contains("timeout") == true -> 
                        "Connection timeout - server may be slow or network issues"
                    e.message?.contains("UnknownHostException") == true -> 
                        "DNS resolution failed - check hostname/IP address"
                    else -> e.message ?: e::class.simpleName
                }
                
                NetworkDiagnosisResult(
                    normalizedBase = base,
                    testPath = "/products",
                    finalUrl = finalUrl,
                    ok = false,
                    message = errorMessage,
                    troubleshootingGuide = ConnectionTroubleshootingGuide.getGuidanceForError(e.message),
                )
            }
        } finally {
            DependencyContainer.configureApiBase(prev)
        }
    }

    suspend fun advancedDiagnose(tempUrl: String): NetworkDiagnosisResult {
        val (normalized, err) = UrlUtils.validateAndNormalizeBaseUrl(tempUrl)
        if (err != null || normalized == null) {
            return NetworkDiagnosisResult(
                normalizedBase = tempUrl,
                testPath = "/products",
                finalUrl = tempUrl,
                ok = false,
                message = err ?: "Invalid URL",
                troubleshootingGuide = ConnectionTroubleshootingGuide.getGuidanceForError(err),
            )
        }
        
        val base = normalized.trimEnd('/')
        val finalUrl = "$base/products"
        
        println("SettingsViewModel: Starting advanced network diagnosis")
        println("SettingsViewModel: Testing URL: $finalUrl")
        
        // Use platform-specific diagnostics that try multiple approaches
        val platformResult = PlatformNetworkDiagnostics.testConnection(finalUrl)
        
        return NetworkDiagnosisResult(
            normalizedBase = base,
            testPath = "/products",
            finalUrl = finalUrl,
            ok = platformResult.success,
            message = platformResult.message + if (platformResult.details != null) " | Preview: ${platformResult.details}" else "",
            troubleshootingGuide = if (!platformResult.success) ConnectionTroubleshootingGuide.getGuidanceForError(platformResult.message) else null,
        )
    }
}
