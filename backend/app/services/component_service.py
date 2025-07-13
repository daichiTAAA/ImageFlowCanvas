import asyncio
import json
import os
import logging
from typing import Dict, Any, List
from app.services.file_service import FileService
from app.models.execution import OutputFile
import uuid

logger = logging.getLogger(__name__)

class ComponentService:
    """
    Component service for ImageFlowCanvas.
    
    Note: According to the architecture design, this service should NOT perform
    direct image processing. Image processing is delegated to Argo Workflows
    which execute containerized processing services.
    
    This service only handles component metadata and coordination.
    """
    def __init__(self):
        self.file_service = FileService()
        # Remove direct processing dependencies - these are now handled by Argo Workflows
        # self.triton_client = TritonYOLOClient(...)  # REMOVED
    
    async def get_component_metadata(self, component_type: str) -> Dict[str, Any]:
        """Get metadata for a component type (parameters, capabilities, etc.)"""
        component_metadata = {
            "resize": {
                "name": "Image Resize",
                "description": "Resize images to specified dimensions",
                "parameters": {
                    "width": {"type": "integer", "default": 800, "min": 1, "max": 4096},
                    "height": {"type": "integer", "default": 600, "min": 1, "max": 4096},
                    "maintain_aspect": {"type": "boolean", "default": True}
                },
                "input_formats": ["jpg", "jpeg", "png", "bmp", "tiff"],
                "output_formats": ["jpg", "png"],
                "container_image": "imageflow/resize-app:latest"
            },
            "ai_detection": {
                "name": "AI Object Detection",
                "description": "Detect objects in images using AI models via Triton Inference Server",
                "parameters": {
                    "model": {"type": "string", "default": "yolo", "options": ["yolo"]},
                    "confidence": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
                    "draw_boxes": {"type": "boolean", "default": True}
                },
                "input_formats": ["jpg", "jpeg", "png"],
                "output_formats": ["jpg", "json"],
                "container_image": "imageflow/triton-detection-app:latest"
            },
            "filter": {
                "name": "Image Filter",
                "description": "Apply filters and effects to images",
                "parameters": {
                    "filter_type": {"type": "string", "default": "blur", "options": ["blur", "sharpen", "edge", "emboss", "grayscale"]},
                    "intensity": {"type": "float", "default": 1.0, "min": 0.0, "max": 5.0}
                },
                "input_formats": ["jpg", "jpeg", "png", "bmp"],
                "output_formats": ["jpg", "png"],
                "container_image": "imageflow/filter-app:latest"
            }
        }
        
        return component_metadata.get(component_type, {})
    
    async def validate_component_parameters(self, component_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize component parameters"""
        metadata = await self.get_component_metadata(component_type)
        param_definitions = metadata.get("parameters", {})
        
        validated_params = {}
        
        for param_name, param_def in param_definitions.items():
            param_type = param_def.get("type")
            default_value = param_def.get("default")
            
            # Get value from parameters or use default
            value = parameters.get(param_name, default_value)
            
            # Type validation and conversion
            if param_type == "integer":
                try:
                    value = int(value)
                    if "min" in param_def:
                        value = max(value, param_def["min"])
                    if "max" in param_def:
                        value = min(value, param_def["max"])
                except (ValueError, TypeError):
                    value = default_value
            elif param_type == "float":
                try:
                    value = float(value)
                    if "min" in param_def:
                        value = max(value, param_def["min"])
                    if "max" in param_def:
                        value = min(value, param_def["max"])
                except (ValueError, TypeError):
                    value = default_value
            elif param_type == "boolean":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    value = bool(value)
            elif param_type == "string":
                if "options" in param_def and value not in param_def["options"]:
                    value = default_value
            
            validated_params[param_name] = value
        
        return validated_params
    
    async def get_available_components(self) -> List[Dict[str, Any]]:
        """Get list of all available components"""
        component_types = ["resize", "ai_detection", "filter"]
        components = []
        
        for component_type in component_types:
            metadata = await self.get_component_metadata(component_type)
            if metadata:
                components.append({
                    "id": component_type,
                    "type": component_type,
                    **metadata
                })
        
        return components
    
    # REMOVED: All direct processing methods have been removed
    # Image processing is now handled by Argo Workflows executing containerized services
    # 
    # The following methods were removed:
    # - async def process_component(...)
    # - async def _process_object_detection(...)
    # - async def _process_resize(...)
    # - async def _process_filter(...)
    #
    # These processing capabilities are now provided by:
    # - services/resize-app/ (for resize operations)
    # - services/object-detection-app/ (for AI detection)
    # - services/filter-app/ (for image filtering)
    #
    # The backend now only coordinates and delegates to Argo Workflows