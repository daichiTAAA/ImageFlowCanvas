package com.imageflow.androidstream.app.ble

import android.bluetooth.le.ScanRecord
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import java.util.UUID

data class EddystoneUid(val namespace: ByteArray, val instance: ByteArray) {
    fun nsHex(): String = namespace.joinToString("") { String.format(Locale.US, "%02x", it) }
    fun instHex(): String = instance.joinToString("") { String.format(Locale.US, "%02x", it) }
}

data class IBeacon(val uuid: UUID, val major: Int, val minor: Int)

object BeaconParsers {
    private const val EDDYSTONE_SVC = 0xFEAA

    fun parseEddystoneUid(record: ScanRecord): EddystoneUid? {
        val svcData = record.getServiceData(android.os.ParcelUuid.fromString(String.format("0000%04x-0000-1000-8000-00805f9b34fb", EDDYSTONE_SVC)))
        if (svcData == null || svcData.size < 20) return null
        if (svcData[0].toInt() != 0x00) return null
        val ns = svcData.copyOfRange(2, 12)
        val inst = svcData.copyOfRange(12, 18)
        return EddystoneUid(ns, inst)
    }

    fun getEddystoneServiceData(record: ScanRecord): ByteArray? =
        record.getServiceData(android.os.ParcelUuid.fromString(String.format("0000%04x-0000-1000-8000-00805f9b34fb", EDDYSTONE_SVC)))

    fun getEddystoneFrameType(record: ScanRecord): Int? {
        val d = getEddystoneServiceData(record) ?: return null
        if (d.isEmpty()) return null
        return d[0].toInt() and 0xFF
    }

    fun toHex(bytes: ByteArray?, sep: String = ""): String {
        if (bytes == null) return ""
        val sb = StringBuilder(bytes.size * (2 + sep.length))
        for (i in bytes.indices) {
            if (i > 0 && sep.isNotEmpty()) sb.append(sep)
            sb.append(String.format("%02x", bytes[i]))
        }
        return sb.toString()
    }

    fun parseIBeacon(record: ScanRecord): IBeacon? {
        val mfg = record.manufacturerSpecificData ?: return null
        for (i in 0 until mfg.size()) {
            val companyId = mfg.keyAt(i)
            val data = mfg.valueAt(i)
            if (companyId == 0x004C && data.size >= 23 && data[0].toInt() == 0x02 && data[1].toInt() == 0x15) {
                val bb = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN)
                bb.position(2)
                val uuidMsb = bb.long
                val uuidLsb = bb.long
                val uuid = UUID(uuidMsb, uuidLsb)
                val major = bb.short.toInt() and 0xFFFF
                val minor = bb.short.toInt() and 0xFFFF
                return IBeacon(uuid, major, minor)
            }
        }
        return null
    }

    fun hexToBytesOrNull(hex: String?): ByteArray? {
        if (hex.isNullOrBlank()) return null
        val s = hex.lowercase(Locale.US).replace("[^0-9a-f]".toRegex(), "")
        if (s.length % 2 != 0) return null
        return ByteArray(s.length / 2) { idx ->
            s.substring(idx * 2, idx * 2 + 2).toInt(16).toByte()
        }
    }
}
