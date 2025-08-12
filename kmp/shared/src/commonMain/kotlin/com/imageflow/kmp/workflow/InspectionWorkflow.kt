package com.imageflow.kmp.workflow

import com.imageflow.kmp.state.InspectionState

interface InspectionWorkflow {
    var state: InspectionState
    fun start()
    fun cancel()
}

