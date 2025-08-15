package com.imageflow.kmp.network

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.assertFalse
import com.imageflow.kmp.util.UrlUtils

class NetworkDiagnosticsTest {
    
    @Test
    fun testUrlValidationAndNormalization() {
        // Test basic URL validation
        val (normalized1, error1) = UrlUtils.validateAndNormalizeBaseUrl("http://192.168.0.9:8000")
        assertEquals("http://192.168.0.9:8000/v1", normalized1)
        assertEquals(null, error1)
        
        // Test URL with existing /api/v1
        val (normalized2, error2) = UrlUtils.validateAndNormalizeBaseUrl("http://10.0.2.2:8000/v1")
        assertEquals("http://10.0.2.2:8000/v1", normalized2)
        assertEquals(null, error2)
        
        // Test invalid URL (no scheme)
        val (normalized3, error3) = UrlUtils.validateAndNormalizeBaseUrl("192.168.0.9:8000")
        assertEquals(null, normalized3)
        assertTrue(error3?.contains("http://") ?: false)
        
        // Test URL with invalid endpoint
        val (normalized4, error4) = UrlUtils.validateAndNormalizeBaseUrl("http://192.168.0.9:8000/v1/products")
        assertEquals(null, normalized4)
        assertTrue(error4?.contains("エンドポイントを含めないでください") ?: false)
    }
    
    @Test
    fun testEmptyUrlValidation() {
        val (normalized, error) = UrlUtils.validateAndNormalizeBaseUrl("")
        assertEquals(null, normalized)
        assertTrue(error?.contains("URLを入力してください") ?: false)
    }
    
    @Test
    fun testWhitespaceHandling() {
        val (normalized, error) = UrlUtils.validateAndNormalizeBaseUrl("  http://192.168.0.9:8000  ")
        assertEquals("http://192.168.0.9:8000/v1", normalized)
        assertEquals(null, error)
    }
    
    @Test
    fun testHttpsSupport() {
        val (normalized, error) = UrlUtils.validateAndNormalizeBaseUrl("https://api.example.com")
        assertEquals("https://api.example.com/v1", normalized)
        assertEquals(null, error)
    }
    
    @Test
    fun testLocalhostVariations() {
        // Test localhost
        val (normalized1, error1) = UrlUtils.validateAndNormalizeBaseUrl("http://localhost:8000")
        assertEquals("http://localhost:8000/v1", normalized1)
        assertEquals(null, error1)
        
        // Test 127.0.0.1
        val (normalized2, error2) = UrlUtils.validateAndNormalizeBaseUrl("http://127.0.0.1:8000")
        assertEquals("http://127.0.0.1:8000/v1", normalized2)
        assertEquals(null, error2)
        
        // Test emulator host
        val (normalized3, error3) = UrlUtils.validateAndNormalizeBaseUrl("http://10.0.2.2:8000")
        assertEquals("http://10.0.2.2:8000/v1", normalized3)
        assertEquals(null, error3)
    }
}
