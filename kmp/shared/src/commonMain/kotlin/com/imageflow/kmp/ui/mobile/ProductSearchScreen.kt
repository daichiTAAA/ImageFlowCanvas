package com.imageflow.kmp.ui.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.imageflow.kmp.models.ProductInfo
import com.imageflow.kmp.network.ProductSuggestion

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProductSearchScreen(
    isLoading: Boolean,
    suggestions: List<ProductSuggestion>,
    searchResults: List<ProductInfo>,
    onQueryChange: (String) -> Unit,
    onSearch: (String) -> Unit,
    onAdvancedSearch: (productType: String, machineNumber: String) -> Unit,
    onSelectProduct: (ProductInfo) -> Unit,
    onBack: () -> Unit
) {
    var query by remember { mutableStateOf("") }
    var productType by remember { mutableStateOf("") }
    var machineNumber by remember { mutableStateOf("") }

    // Load latest list by default (productionDate, monthlySequence desc)
    var initialLoaded by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        if (!initialLoaded) {
            onAdvancedSearch("", "")
            initialLoaded = true
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("順序情報取得", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "戻る")
                    }
                }
            )
        }
    ) { inner ->
        Column(
            modifier = Modifier
                .padding(inner)
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedTextField(
                value = query,
                onValueChange = {
                    query = it
                    onQueryChange(it)
                },
                label = { Text("指図番号 / 型式 / 機番 で検索") },
                singleLine = true,
                trailingIcon = {
                    IconButton(onClick = { onSearch(query) }) {
                        Icon(Icons.Filled.Search, contentDescription = "検索")
                    }
                },
                modifier = Modifier.fillMaxWidth()
            )

            // Manual filters: productType and machineNumber
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(
                    value = productType,
                    onValueChange = { productType = it },
                    label = { Text("型式コード (productType)") },
                    singleLine = true,
                    modifier = Modifier.weight(1f)
                )
                OutlinedTextField(
                    value = machineNumber,
                    onValueChange = { machineNumber = it },
                    label = { Text("機番 (machineNumber)") },
                    singleLine = true,
                    modifier = Modifier.weight(1f)
                )
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                TextButton(onClick = { onAdvancedSearch(productType, machineNumber) }) {
                    Icon(Icons.Filled.Search, contentDescription = null)
                    Spacer(Modifier.width(4.dp))
                    Text("詳細条件で検索")
                }
            }

            if (isLoading) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }

            if (suggestions.isNotEmpty()) {
                Text(text = "サジェスト", style = MaterialTheme.typography.labelLarge)
                LazyColumn(
                    modifier = Modifier.heightIn(max = 160.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(suggestions) { s ->
                        SuggestionItem(s) {
                            query = s.displayText
                            onSearch(s.displayText)
                        }
                    }
                }
            }

            Divider()

            Text(text = "検索結果 (生産日・月連番の降順)", style = MaterialTheme.typography.labelLarge)
            if (searchResults.isEmpty() && !isLoading) {
                Text(
                    text = "一致する製品が見つかりません",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(searchResults) { p ->
                        ProductResultItem(product = p) { onSelectProduct(p) }
                    }
                }
            }
        }
    }
}

@Composable
private fun SuggestionItem(s: ProductSuggestion, onClick: () -> Unit) {
    OutlinedButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(text = s.displayText, fontWeight = FontWeight.Medium)
            Text(
                text = "${s.productType} / ${s.machineNumber}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun ProductResultItem(product: ProductInfo, onClick: () -> Unit) {
    ElevatedCard(onClick = onClick) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(text = "${product.productType} - ${product.machineNumber}", fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(2.dp))
            Text(
                text = "指図: ${product.workOrderId} / 指示: ${product.instructionId}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(2.dp))
            Text(
                text = "生産日: ${product.productionDate} / 連番: ${product.monthlySequence}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
