package com.imageflow.kmp.util

object UrlUtils {
    // Validate and normalize base URL. Ensures scheme and appends "/api/v1" if missing.
    // Returns Pair(normalizedUrl, errorMessage). If errorMessage != null, url is invalid.
    fun validateAndNormalizeBaseUrl(input: String): Pair<String?, String?> {
        val raw = input.trim()
        if (raw.isEmpty()) return null to "URLを入力してください"

        val withScheme = raw
        // Require scheme
        if (!withScheme.startsWith("http://") && !withScheme.startsWith("https://"))
            return null to "http:// または https:// から始めてください"

        // Basic host/path split
        val noScheme = withScheme.removePrefix("http://").removePrefix("https://")
        if (noScheme.isEmpty() || noScheme.startsWith("/")) return null to "ホスト名が不正です"
        val slashIdx = noScheme.indexOf('/')
        val hostPort = if (slashIdx >= 0) noScheme.substring(0, slashIdx) else noScheme
        val path = if (slashIdx >= 0) noScheme.substring(slashIdx) else ""
        if (hostPort.isBlank()) return null to "ホスト名が不正です"

        // Reject when path includes endpoint segments beyond /api/v1
        val pathTrim = path.trimEnd('/')
        if (pathTrim.isNotEmpty() && pathTrim != "/api/v1") {
            return null to "ベースURLにはエンドポイントを含めないでください（例: http://HOST:PORT/api/v1）"
        }

        // Normalize trailing/leading slashes
        var normalized = (withScheme.substring(0, withScheme.indexOf(hostPort)) + hostPort).trimEnd('/')
        if (!normalized.endsWith("/api/v1")) {
            normalized = "$normalized/api/v1"
        }
        return normalized to null
    }
}
