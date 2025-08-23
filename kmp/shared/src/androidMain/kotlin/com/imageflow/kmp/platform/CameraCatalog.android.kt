package com.imageflow.kmp.platform

import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import androidx.core.content.ContextCompat
import com.imageflow.kmp.database.AndroidDbContextHolder

actual fun listAvailableCameras(): List<CameraDeviceInfo> {
    return try {
        val ctx: Context = AndroidDbContextHolder.context
        val cm = ContextCompat.getSystemService(ctx, CameraManager::class.java) ?: return emptyList()
        cm.cameraIdList.mapNotNull { id ->
            try {
                val chars = cm.getCameraCharacteristics(id)
                val facing = when (chars.get(CameraCharacteristics.LENS_FACING)) {
                    CameraCharacteristics.LENS_FACING_BACK -> "Back"
                    CameraCharacteristics.LENS_FACING_FRONT -> "Front"
                    CameraCharacteristics.LENS_FACING_EXTERNAL -> "External"
                    else -> "Unknown"
                }
                CameraDeviceInfo(id = id, label = "$id: $facing")
            } catch (_: Exception) { null }
        }
    } catch (_: Exception) { emptyList() }
}

