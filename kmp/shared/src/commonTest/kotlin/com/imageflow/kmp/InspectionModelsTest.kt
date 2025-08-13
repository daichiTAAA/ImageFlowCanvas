package com.imageflow.kmp

import com.imageflow.kmp.models.*
import com.imageflow.kmp.state.InspectionState
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.assertFalse

class InspectionModelsTest {
    
    @Test
    fun testProductInfoIdGeneration() {
        val productInfo = ProductInfo(
            workOrderId = "WORK001",
            instructionId = "INST001",
            productType = "TYPE-A",
            machineNumber = "MACHINE-123",
            productionDate = "2024-01-15",
            monthlySequence = 1
        )
        
        val expectedId = "WORK001_INST001_MACHINE-123_1"
        assertEquals(expectedId, productInfo.generateId())
    }
    
    @Test
    fun testInspectionStateTransitions() {
        // Test valid state transitions
        assertTrue(InspectionState.ProductScanning.canProgressTo(InspectionState.ProductIdentified))
        assertTrue(InspectionState.ProductIdentified.canProgressTo(InspectionState.InProgress))
        assertTrue(InspectionState.InProgress.canProgressTo(InspectionState.AiCompleted))
        assertTrue(InspectionState.AiCompleted.canProgressTo(InspectionState.HumanReview))
        assertTrue(InspectionState.HumanReview.canProgressTo(InspectionState.Completed))
        
        // Test invalid state transitions
        assertFalse(InspectionState.ProductScanning.canProgressTo(InspectionState.AiCompleted))
        assertFalse(InspectionState.Completed.canProgressTo(InspectionState.InProgress))
        assertFalse(InspectionState.Failed.canProgressTo(InspectionState.InProgress))
    }
    
    @Test
    fun testInspectionStateTerminalStates() {
        // Terminal states
        assertTrue(InspectionState.Completed.isTerminal())
        assertTrue(InspectionState.Failed.isTerminal())
        assertTrue(InspectionState.Cancelled.isTerminal())
        assertTrue(InspectionState.ProductNotFound.isTerminal())
        assertTrue(InspectionState.QrDecodeFailed.isTerminal())
        
        // Non-terminal states
        assertFalse(InspectionState.ProductScanning.isTerminal())
        assertFalse(InspectionState.ProductIdentified.isTerminal())
        assertFalse(InspectionState.InProgress.isTerminal())
        assertFalse(InspectionState.AiCompleted.isTerminal())
        assertFalse(InspectionState.HumanReview.isTerminal())
    }
    
    @Test
    fun testAiInspectionResultCreation() {
        val defects = listOf(
            DetectedDefect(
                type = DefectType.SURFACE_DAMAGE,
                location = BoundingBox(0.1f, 0.2f, 0.3f, 0.4f),
                severity = DefectSeverity.MAJOR,
                confidence = 0.85f,
                description = "Surface scratch detected"
            )
        )
        
        val measurements = listOf(
            Measurement(
                type = MeasurementType.LENGTH,
                value = 10.5f,
                unit = "mm",
                tolerance = FloatRange(10.0f, 11.0f),
                withinTolerance = true
            )
        )
        
        val aiResult = AiInspectionResult(
            overallResult = InspectionResult.FAIL,
            detectedDefects = defects,
            measurements = measurements,
            confidence = 0.9f,
            processingTimeMs = 1500L,
            pipelineId = "pipeline-001"
        )
        
        assertEquals(InspectionResult.FAIL, aiResult.overallResult)
        assertEquals(1, aiResult.detectedDefects.size)
        assertEquals(1, aiResult.measurements.size)
        assertEquals(0.9f, aiResult.confidence)
        assertEquals(1500L, aiResult.processingTimeMs)
        assertEquals("pipeline-001", aiResult.pipelineId)
    }
    
    @Test
    fun testInspectionCreation() {
        val now = System.currentTimeMillis()
        
        val inspection = Inspection(
            id = "inspection-001",
            productId = "product-001",
            workOrderId = "WORK001",
            instructionId = "INST001",
            inspectionType = InspectionType.STATIC_IMAGE,
            inspectionState = InspectionState.ProductIdentified,
            startedAt = now,
            createdAt = now,
            updatedAt = now
        )
        
        assertEquals("inspection-001", inspection.id)
        assertEquals("product-001", inspection.productId)
        assertEquals("WORK001", inspection.workOrderId)
        assertEquals("INST001", inspection.instructionId)
        assertEquals(InspectionType.STATIC_IMAGE, inspection.inspectionType)
        assertEquals(InspectionState.ProductIdentified, inspection.inspectionState)
        assertFalse(inspection.humanVerified)
        assertFalse(inspection.synced)
        assertEquals(0, inspection.syncAttempts)
    }
    
    @Test
    fun testQrScanResultValidation() {
        val productInfo = ProductInfo(
            workOrderId = "WORK001",
            instructionId = "INST001",
            productType = "TYPE-A",
            machineNumber = "MACHINE-123",
            productionDate = "2024-01-15",
            monthlySequence = 1
        ).let { it.copy(id = it.generateId()) }
        
        val successfulScan = QrScanResult(
            success = true,
            productInfo = productInfo,
            rawData = "WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1",
            scanType = ScanType.QR_CODE,
            confidence = 0.95f,
            validationStatus = ValidationStatus.VALID
        )
        
        assertTrue(successfulScan.success)
        assertEquals(productInfo, successfulScan.productInfo)
        assertEquals(ScanType.QR_CODE, successfulScan.scanType)
        assertEquals(ValidationStatus.VALID, successfulScan.validationStatus)
        
        val failedScan = QrScanResult(
            success = false,
            productInfo = null,
            rawData = "invalid-data",
            scanType = ScanType.QR_CODE,
            confidence = 0f,
            validationStatus = ValidationStatus.INVALID,
            errorMessage = "Invalid QR format"
        )
        
        assertFalse(failedScan.success)
        assertEquals(null, failedScan.productInfo)
        assertEquals(ValidationStatus.INVALID, failedScan.validationStatus)
        assertEquals("Invalid QR format", failedScan.errorMessage)
    }
}