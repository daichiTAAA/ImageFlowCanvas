package com.imageflow.kmp.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat

/**
 * Minimal RTMP publisher stub. This uses com.pedroSG94.rtmp-rtsp-stream-client-java.
 * Add dependency in androidApp/build.gradle.kts:
 *   implementation("com.github.pedroSG94.rtmp-rtsp-stream-client-java:rtplibrary:2.3.9")
 *   implementation("com.github.pedroSG94.rtmp-rtsp-stream-client-java:encoder:2.3.9")
 *
 * Then a simple RTMP URL is: rtmp://<host>:1935/live/uplink/<deviceId>
 * (Enable RTMP in MediaMTX if you want to use RTMP instead of WHIP.)
 */
@Composable
fun ThinkletStreamingScreen(
    defaultUrl: String,
    onBack: () -> Unit
) {
    val activity = LocalContext.current as ComponentActivity
    var rtmpUrl by remember { mutableStateOf(defaultUrl) }
    var hasPerm by remember { mutableStateOf(false) }

    val permLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions(),
        onResult = { res ->
            hasPerm = res.values.all { it }
        }
    )

    LaunchedEffect(Unit) {
        val needed = mutableListOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO
        )
        if (Build.VERSION.SDK_INT >= 28) {
            // no-op, network permissions already in manifest
        }
        val missing = needed.filter {
            ContextCompat.checkSelfPermission(activity, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) hasPerm = true else permLauncher.launch(missing.toTypedArray())
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text = "カメラ 映像配信 (RTMP/WHIP 準備)")
        OutlinedTextField(
            value = rtmpUrl,
            onValueChange = { rtmpUrl = it },
            label = { Text("配信URL (例: http://<host>:8889/whip/uplink/<deviceId> or rtmp://<host>:1935/uplink/<deviceId>)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { /* TODO: Start publishing with chosen method */ }, enabled = hasPerm) {
                Text("配信開始")
            }
            Button(onClick = { /* TODO: Stop publishing */ }) {
                Text("停止")
            }
            Button(onClick = onBack) { Text("戻る") }
        }
        Text(text = "メモ: このスタブは配信UIのみ。実配信はRTMPまたはWHIPクライアント実装を追加してください。")
    }
}

