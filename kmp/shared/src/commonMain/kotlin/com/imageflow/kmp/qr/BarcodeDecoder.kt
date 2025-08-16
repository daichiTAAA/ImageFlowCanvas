package com.imageflow.kmp.qr

import com.imageflow.kmp.models.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

// Product info fields aligned with docs:
// - 指図番号: workOrderId
// - 指示番号: instructionId
// - 型式: product_code
// - 機番: machineNumber
// - 生産年月日: productionDate (ISO-8601 string)
// - 月連番: monthlySequence
@Serializable
data class DecodedProductInfo(
    val workOrderId: String?,
    val instructionId: String?,
    val productCode: String?,
    val machineNumber: String?,
    val productionDate: String?,
    val monthlySequence: Int?,
)

interface BarcodeDecoder {
    fun decode(raw: String): DecodedProductInfo
    fun validate(productInfo: DecodedProductInfo): ValidationResult
}

@Serializable
data class ValidationResult(
    val isValid: Boolean,
    val errors: List<ValidationError> = emptyList(),
    val warnings: List<ValidationWarning> = emptyList()
)

@Serializable
data class ValidationError(
    val field: String,
    val message: String,
    val code: String
)

@Serializable
data class ValidationWarning(
    val field: String,
    val message: String,
    val code: String
)

// Default implementation for common QR code formats
class DefaultBarcodeDecoder : BarcodeDecoder {
    private val json = Json { ignoreUnknownKeys = true }
    
    override fun decode(raw: String): DecodedProductInfo {
        return try {
            // Try JSON format first
            if (raw.startsWith("{")) {
                json.decodeFromString<DecodedProductInfo>(raw)
            } else {
                // Try comma-separated format
                parseCommaSeparated(raw)
            }
        } catch (e: Exception) {
            // Return empty result if parsing fails
            DecodedProductInfo(null, null, null, null, null, null)
        }
    }
    
    private fun parseCommaSeparated(raw: String): DecodedProductInfo {
        val parts = raw.split(",").map { it.trim() }
        return DecodedProductInfo(
            workOrderId = parts.getOrNull(0),
            instructionId = parts.getOrNull(1),
            productCode = parts.getOrNull(2),
            machineNumber = parts.getOrNull(3),
            productionDate = parts.getOrNull(4),
            monthlySequence = parts.getOrNull(5)?.toIntOrNull()
        )
    }
    
    override fun validate(productInfo: DecodedProductInfo): ValidationResult {
        val errors = mutableListOf<ValidationError>()
        val warnings = mutableListOf<ValidationWarning>()
        
        // Required field validation
        if (productInfo.workOrderId.isNullOrBlank()) {
            errors.add(ValidationError("workOrderId", "指図番号は必須です", "REQUIRED_FIELD"))
        }
        if (productInfo.instructionId.isNullOrBlank()) {
            errors.add(ValidationError("instructionId", "指示番号は必須です", "REQUIRED_FIELD"))
        }
        if (productInfo.productCode.isNullOrBlank()) {
            errors.add(ValidationError("productCode", "型式は必須です", "REQUIRED_FIELD"))
        }
        if (productInfo.machineNumber.isNullOrBlank()) {
            errors.add(ValidationError("machineNumber", "機番は必須です", "REQUIRED_FIELD"))
        }
        
        // Date format validation
        productInfo.productionDate?.let { date ->
            if (!isValidIsoDate(date)) {
                errors.add(ValidationError("productionDate", "生産年月日の形式が正しくありません (YYYY-MM-DD)", "INVALID_FORMAT"))
            }
        }
        
        // Monthly sequence validation
        productInfo.monthlySequence?.let { sequence ->
            if (sequence <= 0) {
                warnings.add(ValidationWarning("monthlySequence", "月連番が0以下です", "SUSPICIOUS_VALUE"))
            }
        }
        
        return ValidationResult(
            isValid = errors.isEmpty(),
            errors = errors,
            warnings = warnings
        )
    }
    
    private fun isValidIsoDate(date: String): Boolean {
        return try {
            val pattern = Regex("""^\d{4}-\d{2}-\d{2}$""")
            pattern.matches(date)
        } catch (e: Exception) {
            false
        }
    }
}

// Extension function to convert decoded info to ProductInfo
fun DecodedProductInfo.toProductInfo(): ProductInfo? {
    return if (workOrderId != null && instructionId != null && 
               productCode != null && machineNumber != null && 
               productionDate != null && monthlySequence != null) {
        ProductInfo(
            workOrderId = workOrderId,
            instructionId = instructionId,
            productCode = productCode,
            machineNumber = machineNumber,
            productionDate = productionDate,
            monthlySequence = monthlySequence
        ).let {
            it.copy(id = it.generateId())
        }
    } else {
        null
    }
}
