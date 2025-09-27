package com.imageflow.thinklet.app.streaming

import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

object WhipUrlUtils {
    fun normalize(raw: String): String {
        val parsed = raw.toHttpUrlOrNull()
        if (parsed != null) {
            val segs = parsed.encodedPathSegments.filter { it.isNotEmpty() }.toMutableList()
            if (segs.firstOrNull() == "whip" || segs.firstOrNull() == "whep") {
                segs.removeAt(0)
            }
            if (segs.lastOrNull() != "whip") {
                segs.add("whip")
            }
            val builder = parsed.newBuilder().encodedPath("/")
            segs.forEach { builder.addPathSegment(it) }
            return builder.build().toString()
        }
        var s = raw.trim()
        s = s.replace(Regex("/whip/+"), "/")
        return if (s.endsWith("/whip")) s else if (s.endsWith('/')) s + "whip" else "$s/whip"
    }

    fun extractOrigin(raw: String): String? {
        val u = raw.toHttpUrlOrNull() ?: return null
        val defaultPort = if (u.isHttps) 443 else 80
        val portPart = if (u.port != defaultPort) ":${u.port}" else ""
        return "${u.scheme}://${u.host}$portPart"
    }
}
