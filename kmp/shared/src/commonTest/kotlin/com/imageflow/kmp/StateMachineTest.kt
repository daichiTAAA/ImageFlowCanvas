package com.imageflow.kmp

import com.imageflow.kmp.state.InspectionState
import kotlin.test.Test
import kotlin.test.assertTrue

class StateMachineTest {
    @Test
    fun transitions_can_be_represented() {
        val states = listOf(
            InspectionState.ProductScanning,
            InspectionState.ProductIdentified,
            InspectionState.InProgress,
            InspectionState.AiCompleted,
            InspectionState.HumanReview,
            InspectionState.Completed,
        )
        assertTrue(states.isNotEmpty())
    }
}

