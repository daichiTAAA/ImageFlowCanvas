package com.imageflow.kmp.usecase

import com.imageflow.kmp.models.Inspection
import com.imageflow.kmp.repository.InspectionRepository

class ExecuteInspectionUseCase(private val repo: InspectionRepository) {
    suspend operator fun invoke(inspection: Inspection) {
        // Placeholder for pipeline execution logic (see docs 0310 §3.1.3)
        repo.saveInspection(inspection)
    }
}
