package com.imageflow.kmp.util

object UrlUtils {
    // Validate and normalize base URL. Ensures scheme and appends "/api/v1" if missing.
    // Returns Pair(normalizedUrl, errorMessage). If errorMessage != null, url is invalid.
    fun validateAndNormalizeBaseUrl(input: String): Pair<String?, String?> {
        val raw = input.trim()
        if (raw.isEmpty()) return null to "URLを入力してください"

        val withScheme = if (raw.startsWith("http://") || raw.startsWith("https://")) raw else raw
        // Require scheme
        if (!withScheme.startsWith("http://") && !withScheme.startsWith("https://"))
            return null to "http:// または https:// から始めてください"

        // Basic host check
        val parts = withScheme.removePrefix("http://").removePrefix("https://")
        if (parts.isEmpty() || parts.startsWith("/")) return null to "ホスト名が不正です"

        // Normalize trailing/leading slashes
        var normalized = withScheme.trimEnd('/')
        if (!normalized.endsWith("/api/v1")) {
            normalized = "$normalized/api/v1"
        }
        return normalized to null
    }
}

