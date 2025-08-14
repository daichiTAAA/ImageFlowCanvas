package com.imageflow.kmp.util

/**
 * Network debugging utilities to help diagnose connectivity issues
 */
object NetworkDebugUtils {
    
    fun getNetworkEnvironmentInfo(): String {
        val info = mutableListOf<String>()
        
        // System properties that might affect networking
        info.add("=== Network Environment Debug Info ===")
        
        try {
            val proxyHost = System.getProperty("http.proxyHost", "")
            val proxyPort = System.getProperty("http.proxyPort", "")
            val httpsProxyHost = System.getProperty("https.proxyHost", "")
            val httpsProxyPort = System.getProperty("https.proxyPort", "")
            val nonProxyHosts = System.getProperty("http.nonProxyHosts", "")
            
            info.add("HTTP Proxy Host: '$proxyHost'")
            info.add("HTTP Proxy Port: '$proxyPort'") 
            info.add("HTTPS Proxy Host: '$httpsProxyHost'")
            info.add("HTTPS Proxy Port: '$httpsProxyPort'")
            info.add("Non-Proxy Hosts: '$nonProxyHosts'")
            
            // Network-related system properties
            val useSystemProxies = System.getProperty("java.net.useSystemProxies", "false")
            info.add("Use System Proxies: $useSystemProxies")
            
        } catch (e: Exception) {
            info.add("Error reading system properties: ${e.message}")
        }
        
        return info.joinToString("\n")
    }
    
    fun clearProxySettings() {
        try {
            println("NetworkDebugUtils: Clearing proxy settings...")
            System.setProperty("http.proxyHost", "")
            System.setProperty("http.proxyPort", "")
            System.setProperty("https.proxyHost", "")
            System.setProperty("https.proxyPort", "")
            System.setProperty("http.nonProxyHosts", "*")
            System.setProperty("java.net.useSystemProxies", "false")
            println("NetworkDebugUtils: Proxy settings cleared")
        } catch (e: Exception) {
            println("NetworkDebugUtils: Error clearing proxy settings: ${e.message}")
        }
    }
    
    fun validateUrl(url: String): List<String> {
        val issues = mutableListOf<String>()
        
        if (url.isEmpty()) {
            issues.add("URL is empty")
            return issues
        }
        
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            issues.add("URL must start with http:// or https://")
        }
        
        if (url.contains("localhost") && !url.contains("localhost:")) {
            issues.add("localhost URLs should specify a port (e.g., localhost:8000)")
        }
        
        if (url.contains(":80/") || url.endsWith(":80")) {
            issues.add("WARNING: Port 80 detected - this might indicate proxy interference")
        }
        
        if (url.contains("127.0.0.1:80")) {
            issues.add("CRITICAL: localhost:80 detected - likely proxy redirect issue")
        }
        
        val pathParts = url.split("/")
        if (pathParts.size > 5 && pathParts.contains("products")) {
            issues.add("URL appears to contain endpoint path - use base URL only")
        }
        
        return issues
    }
}