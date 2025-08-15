package com.imageflow.kmp.ui.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.imageflow.kmp.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.launch
import androidx.compose.runtime.rememberCoroutineScope

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    initialBaseUrl: String,
    onApply: (String) -> Unit,
    onTest: suspend (String) -> com.imageflow.kmp.ui.viewmodel.ConnectionTestResult,
    onResetDefault: () -> Unit,
    onDiagnose: suspend (String) -> com.imageflow.kmp.ui.viewmodel.NetworkDiagnosisResult,
    onBack: () -> Unit,
) {
    var url by remember { mutableStateOf(initialBaseUrl) }
    var saved by remember { mutableStateOf(false) }
    var testing by remember { mutableStateOf(false) }
    var testResult by remember { mutableStateOf<String?>(null) }
    var testError by remember { mutableStateOf<String?>(null) }
    var validationError by remember { mutableStateOf<String?>(null) }
    var diag by remember { mutableStateOf<com.imageflow.kmp.ui.viewmodel.NetworkDiagnosisResult?>(null) }
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("設定", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text("戻る") }
                }
            )
        }
    ) { inner ->
        val scrollState = rememberScrollState()
        Column(
            modifier = Modifier
                .padding(inner)
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(text = "API ベースURL", style = MaterialTheme.typography.labelLarge)
            OutlinedTextField(
                value = url,
                onValueChange = { value ->
                    url = value
                    saved = false
                    // simple live validation: reuse same logic as VM utility for user feedback
                    val v = com.imageflow.kmp.util.UrlUtils.validateAndNormalizeBaseUrl(value)
                    validationError = v.second
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("http://10.0.2.2:8000/v1") }
            )
            if (validationError != null) {
                Text(
                    text = validationError!!,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    onApply(url.trim())
                    saved = true
                }, enabled = validationError == null) { Text("保存") }
                if (saved) Text("保存しました", color = MaterialTheme.colorScheme.primary)
                OutlinedButton(onClick = {
                    onResetDefault()
                    testResult = null
                    testError = null
                    validationError = null
                    saved = true
                }) { Text("既定値に戻す") }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    enabled = !testing && validationError == null,
                    onClick = {
                        testing = true
                        testResult = null
                        testError = null
                        diag = null
                        scope.launch {
                            val res = try { onTest(url.trim()) } catch (e: Exception) { com.imageflow.kmp.ui.viewmodel.ConnectionTestResult(false, e.message) }
                            testResult = if (res.ok) "OK" else "NG"
                            testError = if (res.ok) null else (res.message ?: "接続に失敗しました")
                            testing = false
                        }
                    }
                ) { Text(if (testing) "テスト中..." else "接続テスト") }
                if (testResult != null) {
                    val color = if (testResult == "OK") MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                    Text("結果: $testResult", color = color)
                }
            }
            if (!testing && testResult == "NG" && testError != null) {
                Text(
                    text = "理由: $testError",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = {
                    scope.launch {
                        diag = onDiagnose(url.trim())
                    }
                }) { Text("詳細診断") }
            }
            diag?.let { d ->
                ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Normalized Base: ${d.normalizedBase}")
                        Text("Test Path: ${d.testPath}")
                        Text("Final URL: ${d.finalUrl}")
                        val okColor = if (d.ok) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                        Text("OK: ${d.ok}", color = okColor)
                        d.message?.let { Text("Message: $it", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    }
                }
            }
            Divider()
            Text(
                text = "ヒント: エミュレータは 10.0.2.2、実機はPCのLAN IPを使用。ベースURLは /v1 まで（/products は含めない）。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
