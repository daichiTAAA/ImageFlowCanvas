package com.imageflow.kmp.network.ktor

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.statement.HttpResponse
import io.ktor.http.isSuccess
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import java.net.Proxy
import java.net.InetSocketAddress
import java.util.concurrent.TimeUnit
import okhttp3.Dns
import java.net.InetAddress

/**
 * Enhanced network diagnostic client for Android that tries multiple approaches
 * to bypass proxy and DNS issues that cause localhost:80 redirects
 */
class AndroidNetworkDiagnosticClient {
    
    private fun createDiagnosticClient(useSystemDns: Boolean = true): HttpClient {
        return HttpClient(OkHttp) {
            engine {
                config {
                    // Completely disable all proxy configurations
                    proxy(Proxy.NO_PROXY)
                    
                    // Clear system proxy properties
                    System.setProperty("http.proxyHost", "")
                    System.setProperty("http.proxyPort", "")
                    System.setProperty("https.proxyHost", "")
                    System.setProperty("https.proxyPort", "")
                    System.setProperty("http.nonProxyHosts", "*")
                    
                    // Use custom DNS if requested
                    if (!useSystemDns) {
                        dns(object : Dns {
                            override fun lookup(hostname: String): List<InetAddress> {
                                return try {
                                    // Try to resolve using system DNS directly
                                    InetAddress.getAllByName(hostname).toList()
                                } catch (e: Exception) {
                                    // If system DNS fails, try some fallbacks
                                    when {
                                        hostname == "10.0.2.2" -> listOf(InetAddress.getByName("10.0.2.2"))
                                        hostname.startsWith("192.168.") -> listOf(InetAddress.getByName(hostname))
                                        hostname.startsWith("10.") -> listOf(InetAddress.getByName(hostname))
                                        hostname.startsWith("172.") -> listOf(InetAddress.getByName(hostname))
                                        else -> throw e
                                    }
                                }
                            }
                        })
                    }
                    
                    // Aggressive timeout settings
                    connectTimeout(15, TimeUnit.SECONDS)
                    readTimeout(15, TimeUnit.SECONDS)
                    writeTimeout(15, TimeUnit.SECONDS)
                    
                    // Disable redirects to catch any localhost:80 redirects
                    followRedirects(false)
                }
            }
            
            install(HttpTimeout) {
                requestTimeoutMillis = 15000
                connectTimeoutMillis = 15000
                socketTimeoutMillis = 15000
            }
            
            install(ContentNegotiation) {
                json(Json { 
                    ignoreUnknownKeys = true
                    isLenient = true
                })
            }
            
            install(Logging) { 
                level = LogLevel.ALL
            }
        }
    }
    
    suspend fun testConnection(url: String): DiagnosticResult {
        val results = mutableListOf<String>()
        
        // Try with system DNS first
        val systemDnsResult = tryConnection(url, createDiagnosticClient(true), "System DNS")
        results.add("System DNS: ${systemDnsResult.message}")
        
        if (systemDnsResult.success) {
            return systemDnsResult
        }
        
        // Try with custom DNS as fallback
        val customDnsResult = tryConnection(url, createDiagnosticClient(false), "Custom DNS")
        results.add("Custom DNS: ${customDnsResult.message}")
        
        return DiagnosticResult(
            success = customDnsResult.success,
            message = if (customDnsResult.success) customDnsResult.message else results.joinToString("; "),
            responseBody = customDnsResult.responseBody
        )
    }
    
    private suspend fun tryConnection(url: String, client: HttpClient, method: String): DiagnosticResult {
        return try {
            println("AndroidNetworkDiagnostic: Trying $method for URL: $url")
            
            val startTime = System.currentTimeMillis()
            val response: HttpResponse = client.get(url)
            val duration = System.currentTimeMillis() - startTime
            
            println("AndroidNetworkDiagnostic: $method response status: ${response.status}")
            println("AndroidNetworkDiagnostic: $method response headers: ${response.headers}")
            
            if (!response.status.isSuccess()) {
                val errorBody = try {
                    response.body<String>()
                } catch (e: Exception) {
                    "Unable to read error body: ${e.message}"
                }
                DiagnosticResult(
                    success = false,
                    message = "$method failed: HTTP ${response.status.value} ${response.status.description} (${duration}ms)",
                    responseBody = errorBody
                )
            } else {
                val responseBody = response.body<String>()
                DiagnosticResult(
                    success = true,
                    message = "$method succeeded in ${duration}ms (${responseBody.length} chars)",
                    responseBody = responseBody
                )
            }
        } catch (e: Exception) {
            println("AndroidNetworkDiagnostic: $method failed with exception: ${e.message}")
            e.printStackTrace()
            
            val errorMessage = when {
                e.message?.contains("localhost") == true || e.message?.contains("127.0.0.1") == true -> 
                    "$method: Connection redirected to localhost:80 - proxy interference detected"
                e.message?.contains("Connection refused") == true -> 
                    "$method: Connection refused - server unreachable"
                e.message?.contains("timeout") == true -> 
                    "$method: Connection timeout"
                e.message?.contains("UnknownHostException") == true -> 
                    "$method: DNS resolution failed"
                else -> "$method: ${e.message ?: e::class.simpleName}"
            }
            
            DiagnosticResult(
                success = false,
                message = errorMessage,
                responseBody = null
            )
        } finally {
            try {
                client.close()
            } catch (e: Exception) {
                // Ignore close errors
            }
        }
    }
    
    data class DiagnosticResult(
        val success: Boolean,
        val message: String,
        val responseBody: String?
    )
}