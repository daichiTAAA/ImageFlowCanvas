package com.imageflow.kmp

import com.imageflow.kmp.models.*
import com.imageflow.kmp.qr.DefaultBarcodeDecoder
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.assertFalse

class QrDecoderTest {
    
    private val decoder = DefaultBarcodeDecoder()
    
    @Test
    fun testValidCommaSeparatedQrCode() {
        val rawData = "WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1"
        val result = decoder.decode(rawData)
        
        assertEquals("WORK001", result.workOrderId)
        assertEquals("INST001", result.instructionId)
        assertEquals("TYPE-A", result.productType)
        assertEquals("MACHINE-123", result.machineNumber)
        assertEquals("2024-01-15", result.productionDate)
        assertEquals(1, result.monthlySequence)
    }
    
    @Test
    fun testValidJsonQrCode() {
        val rawData = """{"workOrderId":"WORK002","instructionId":"INST002","productType":"TYPE-B","machineNumber":"MACHINE-456","productionDate":"2024-02-20","monthlySequence":5}"""
        val result = decoder.decode(rawData)
        
        assertEquals("WORK002", result.workOrderId)
        assertEquals("INST002", result.instructionId)
        assertEquals("TYPE-B", result.productType)
        assertEquals("MACHINE-456", result.machineNumber)
        assertEquals("2024-02-20", result.productionDate)
        assertEquals(5, result.monthlySequence)
    }
    
    @Test
    fun testValidationWithValidData() {
        val productInfo = DecodedProductInfo(
            workOrderId = "WORK001",
            instructionId = "INST001",
            productType = "TYPE-A",
            machineNumber = "MACHINE-123",
            productionDate = "2024-01-15",
            monthlySequence = 1
        )
        
        val validationResult = decoder.validate(productInfo)
        assertTrue(validationResult.isValid)
        assertTrue(validationResult.errors.isEmpty())
    }
    
    @Test
    fun testValidationWithMissingRequiredFields() {
        val productInfo = DecodedProductInfo(
            workOrderId = null,
            instructionId = "INST001",
            productType = "TYPE-A",
            machineNumber = null,
            productionDate = "2024-01-15",
            monthlySequence = 1
        )
        
        val validationResult = decoder.validate(productInfo)
        assertFalse(validationResult.isValid)
        assertEquals(2, validationResult.errors.size) // workOrderId and machineNumber missing
    }
    
    @Test
    fun testValidationWithInvalidDateFormat() {
        val productInfo = DecodedProductInfo(
            workOrderId = "WORK001",
            instructionId = "INST001",
            productType = "TYPE-A",
            machineNumber = "MACHINE-123",
            productionDate = "2024/01/15", // Wrong format
            monthlySequence = 1
        )
        
        val validationResult = decoder.validate(productInfo)
        assertFalse(validationResult.isValid)
        assertEquals(1, validationResult.errors.size)
    }
    
    @Test
    fun testProductInfoConversion() {
        val decodedInfo = DecodedProductInfo(
            workOrderId = "WORK001",
            instructionId = "INST001",
            productType = "TYPE-A",
            machineNumber = "MACHINE-123",
            productionDate = "2024-01-15",
            monthlySequence = 1
        )
        
        val productInfo = decodedInfo.toProductInfo()
        
        assertTrue(productInfo != null)
        assertEquals("WORK001", productInfo!!.workOrderId)
        assertEquals("INST001", productInfo.instructionId)
        assertEquals("TYPE-A", productInfo.productType)
        assertEquals("MACHINE-123", productInfo.machineNumber)
        assertEquals("2024-01-15", productInfo.productionDate)
        assertEquals(1, productInfo.monthlySequence)
        assertEquals("WORK001_INST001_MACHINE-123_1", productInfo.id)
    }
}