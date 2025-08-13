package com.imageflow.kmp.ui.placeholder

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.imageflow.kmp.platform.provideCameraController

// Enhanced UI for ImageFlow KMP - now with visible components
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RootUI() {
    var started by remember { mutableStateOf(false) }
    var cameraStatus by remember { mutableStateOf("初期化中...") }
    val camera = remember { provideCameraController() }
    
    LaunchedEffect(Unit) {
        try {
            camera.start()
            started = true
            cameraStatus = "カメラ起動完了"
        } catch (e: Exception) {
            cameraStatus = "カメラエラー: ${e.message}"
        }
    }

    MaterialTheme {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // App Title
            Text(
                text = "ImageFlow KMP",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 16.dp)
            )
            
            // Status Card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "システム状態",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "カメラ: ",
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            text = cameraStatus,
                            color = if (started) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                        )
                    }
                }
            }

            // Feature List
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "利用可能機能",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.padding(bottom = 12.dp)
                    )
                    
                    LazyColumn {
                        item {
                            FeatureItem("📱", "カメラ制御", "画像キャプチャとプレビュー")
                        }
                        item {
                            FeatureItem("🗄️", "ローカルDB", "SQLDelightによるデータ永続化")
                        }
                        item {
                            FeatureItem("🌐", "ネットワーク", "gRPC/REST/WebSocket通信")
                        }
                        item {
                            FeatureItem("🔍", "画像解析", "AI検出とフィルタリング")
                        }
                        item {
                            FeatureItem("📊", "データ同期", "オフライン対応同期キュー")
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.weight(1f))

            // Footer
            Text(
                text = "ImageFlowCanvas - Kotlin Multiplatform\n画像処理・検査システム",
                textAlign = TextAlign.Center,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 16.dp)
            )
        }
    }
}

@Composable
private fun FeatureItem(
    icon: String,
    title: String,
    description: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = icon,
            fontSize = 20.sp,
            modifier = Modifier.padding(end = 12.dp)
        )
        Column {
            Text(
                text = title,
                fontWeight = FontWeight.Medium,
                fontSize = 16.sp
            )
            Text(
                text = description,
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 2.dp)
            )
        }
    }
}
