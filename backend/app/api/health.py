from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "ImageFlowCanvas API Server"}


@router.get("/health")
async def health_check():
    return {"status": "healthy"}



