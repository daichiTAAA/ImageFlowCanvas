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
import com.imageflow.kmp.platform.listAvailableCameras
import com.imageflow.kmp.settings.AppSettings
import com.imageflow.kmp.platform.CameraDeviceInfo

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    initialBaseUrl: String,
    initialProcessCode: String,
    isAuthenticated: Boolean,
    onApply: (String, String) -> Unit,
    onTest: suspend (String) -> com.imageflow.kmp.ui.viewmodel.ConnectionTestResult,
    onResetDefault: () -> Unit,
    onDiagnose: suspend (String) -> com.imageflow.kmp.ui.viewmodel.NetworkDiagnosisResult,
    onLogin: suspend (String, String) -> Boolean,
    onLogout: () -> Unit,
    processCandidates: List<com.imageflow.kmp.network.ProcessMasterKmp>,
    onLoadProcesses: suspend () -> Unit,
    onBack: () -> Unit,
) {
    var url by remember { mutableStateOf(initialBaseUrl) }
    var process by remember { mutableStateOf(initialProcessCode) }
    var expanded by remember { mutableStateOf(false) }
    var saved by remember { mutableStateOf(false) }
    var testing by remember { mutableStateOf(false) }
    var testResult by remember { mutableStateOf<String?>(null) }
    var testError by remember { mutableStateOf<String?>(null) }
    var validationError by remember { mutableStateOf<String?>(null) }
    var diag by remember { mutableStateOf<com.imageflow.kmp.ui.viewmodel.NetworkDiagnosisResult?>(null) }
    val scope = rememberCoroutineScope()
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var loginError by remember { mutableStateOf<String?>(null) }

    // Camera list and selection (load after composition to allow native logger flush)
    var cameras by remember { mutableStateOf<List<CameraDeviceInfo>>(emptyList()) }
    LaunchedEffect(Unit) {
        val list = listAvailableCameras()
        println("[SettingsScreen] Camera list size: ${list.size}")
        list.forEachIndexed { idx, c -> println("[SettingsScreen] #${idx}: ${c.label}") }
        cameras = list
    }
    var cameraMenuExpanded by remember { mutableStateOf(false) }
    var selectedCameraId by remember { mutableStateOf(AppSettings.getSelectedCameraId() ?: cameras.firstOrNull()?.id.orEmpty()) }
    val selectedCameraLabel = cameras.firstOrNull { it.id == selectedCameraId }?.label ?: (selectedCameraId.ifBlank { "(未選択)" })

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
            // Camera selection
            Text(text = "カメラ選択", style = MaterialTheme.typography.labelLarge)
            ExposedDropdownMenuBox(
                expanded = cameraMenuExpanded,
                onExpandedChange = { cameraMenuExpanded = it }
            ) {
                OutlinedTextField(
                    value = selectedCameraLabel,
                    onValueChange = {},
                    readOnly = true,
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor(),
                    placeholder = { Text("カメラを選択") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = cameraMenuExpanded) }
                )
                ExposedDropdownMenu(expanded = cameraMenuExpanded, onDismissRequest = { cameraMenuExpanded = false }) {
                    if (cameras.isEmpty()) {
                        DropdownMenuItem(text = { Text("検出できるカメラがありません") }, onClick = { cameraMenuExpanded = false }, enabled = false)
                    } else {
                        cameras.forEach { cam ->
                            DropdownMenuItem(
                                text = { Text(cam.label) },
                                onClick = {
                                    selectedCameraId = cam.id
                                    AppSettings.setSelectedCameraId(cam.id)
                                    cameraMenuExpanded = false
                                }
                            )
                        }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))

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
            Spacer(Modifier.height(8.dp))
            Text(text = "工程コード (process_code)", style = MaterialTheme.typography.labelLarge)
            ExposedDropdownMenuBox(
                expanded = expanded,
                onExpandedChange = { isExpanded ->
                    expanded = isExpanded
                    if (isExpanded && processCandidates.isEmpty()) {
                        scope.launch { onLoadProcesses() }
                    }
                }
            ) {
                OutlinedTextField(
                    value = process,
                    onValueChange = { /* readOnly; selection via dropdown */ },
                    readOnly = true,
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor(),
                    placeholder = { Text("") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) }
                )
                ExposedDropdownMenu(
                    expanded = expanded,
                    onDismissRequest = { expanded = false }
                ) {
                    if (processCandidates.isEmpty()) {
                        DropdownMenuItem(
                            text = { Text("候補なし/要ログイン") },
                            onClick = { expanded = false },
                            enabled = false
                        )
                    } else {
                        processCandidates.forEach { p ->
                            DropdownMenuItem(
                                text = { Text("${p.process_name} (${p.process_code})") },
                                onClick = {
                                    process = p.process_code
                                    saved = false
                                    expanded = false
                                }
                            )
                        }
                    }
                }
            }
            if (validationError != null) {
                Text(
                    text = validationError!!,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    onApply(url.trim(), process.trim())
                    saved = true
                }, enabled = validationError == null) { Text("保存") }
                if (saved) Text("保存しました", color = MaterialTheme.colorScheme.primary)
                OutlinedButton(onClick = {
                    onResetDefault()
                    testResult = null
                    testError = null
                    validationError = null
                    saved = true
                    process = "DEFAULT"
                }) { Text("既定値に戻す") }
            }

            HorizontalDivider()
            Text(text = "認証 (JWT)", style = MaterialTheme.typography.labelLarge)
            if (!isAuthenticated) {
                OutlinedTextField(value = username, onValueChange = { username = it }, singleLine = true, modifier = Modifier.fillMaxWidth(), label = { Text("ユーザー名") })
                OutlinedTextField(value = password, onValueChange = { password = it }, singleLine = true, modifier = Modifier.fillMaxWidth(), label = { Text("パスワード") })
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        loginError = null
                        scope.launch {
                            val ok = onLogin(username.trim(), password.trim())
                            if (!ok) loginError = "ログインに失敗しました"
                            else {
                                // After login, try to load processes for dropdown
                                // Use a best-effort pattern: call provided loader via onTest to ensure base URL applied; then fetch processes via a lightweight inline client?
                            }
                        }
                    }) { Text("ログイン") }
                }
                if (loginError != null) {
                    Text(loginError!!, color = MaterialTheme.colorScheme.error)
                }
            } else {
                Text("ログイン済み", color = MaterialTheme.colorScheme.primary)
                OutlinedButton(onClick = { onLogout() }) { Text("ログアウト") }
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
            HorizontalDivider()
            Text(
                text = "ヒント: エミュレータは 10.0.2.2、実機はPCのLAN IPを使用。ベースURLは /v1 まで（/products は含めない）。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
