package com.imageflow.kmp.state

// Based on docs 0310: PRODUCT_SCANNING -> PRODUCT_IDENTIFIED -> IN_PROGRESS -> AI_COMPLETED -> HUMAN_REVIEW -> COMPLETED
sealed class InspectionState {
    data object ProductScanning : InspectionState()
    data object ProductIdentified : InspectionState()
    data object InProgress : InspectionState()
    data object AiCompleted : InspectionState()
    data object HumanReview : InspectionState()
    data object Completed : InspectionState()
    
    // Exceptions
    data object ProductNotFound : InspectionState()
    data object QrDecodeFailed : InspectionState()
    data object Failed : InspectionState()
    data object Cancelled : InspectionState()
}

