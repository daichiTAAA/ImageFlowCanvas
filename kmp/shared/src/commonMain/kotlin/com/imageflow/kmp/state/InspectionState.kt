package com.imageflow.kmp.state

import kotlinx.serialization.Serializable

// Based on docs 0310: PRODUCT_SCANNING -> PRODUCT_IDENTIFIED -> IN_PROGRESS -> AI_COMPLETED -> HUMAN_REVIEW -> COMPLETED
@Serializable
sealed class InspectionState {
    @Serializable
    data object ProductScanning : InspectionState()
    
    @Serializable
    data object ProductIdentified : InspectionState()
    
    @Serializable
    data object InProgress : InspectionState()
    
    @Serializable
    data object AiCompleted : InspectionState()
    
    @Serializable
    data object HumanReview : InspectionState()
    
    @Serializable
    data object Completed : InspectionState()
    
    // Exceptions
    @Serializable
    data object ProductNotFound : InspectionState()
    
    @Serializable
    data object QrDecodeFailed : InspectionState()
    
    @Serializable
    data object Failed : InspectionState()
    
    @Serializable
    data object Cancelled : InspectionState()
}

// Extension functions for state management
fun InspectionState.isTerminal(): Boolean = when (this) {
    is InspectionState.Completed,
    is InspectionState.ProductNotFound,
    is InspectionState.QrDecodeFailed,
    is InspectionState.Failed,
    is InspectionState.Cancelled -> true
    else -> false
}

fun InspectionState.canProgressTo(nextState: InspectionState): Boolean = when (this) {
    is InspectionState.ProductScanning -> nextState is InspectionState.ProductIdentified || 
                                         nextState is InspectionState.QrDecodeFailed ||
                                         nextState is InspectionState.ProductNotFound
    is InspectionState.ProductIdentified -> nextState is InspectionState.InProgress ||
                                           nextState is InspectionState.Cancelled
    is InspectionState.InProgress -> nextState is InspectionState.AiCompleted ||
                                    nextState is InspectionState.Failed ||
                                    nextState is InspectionState.Cancelled
    is InspectionState.AiCompleted -> nextState is InspectionState.HumanReview ||
                                     nextState is InspectionState.Completed
    is InspectionState.HumanReview -> nextState is InspectionState.Completed ||
                                     nextState is InspectionState.Cancelled
    else -> false
}

