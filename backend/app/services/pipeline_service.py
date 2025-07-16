from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pipeline import (
    Pipeline,
    PipelineCreateRequest,
    PipelineUpdateRequest,
    PipelineComponent,
)
from app.models.pipeline_db import PipelineModel
from app.database import get_db
from datetime import datetime


class PipelineService:
    def __init__(self):
        pass

    async def get_all_pipelines(self, db: AsyncSession) -> List[Pipeline]:
        """全パイプラインを取得"""
        result = await db.execute(select(PipelineModel))
        pipeline_models = result.scalars().all()

        return [
            Pipeline(
                id=str(model.id),
                name=model.name,
                description=model.description,
                components=[PipelineComponent(**comp) for comp in model.components],
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in pipeline_models
        ]

    async def get_pipeline(
        self, pipeline_id: str, db: AsyncSession
    ) -> Optional[Pipeline]:
        """特定のパイプラインを取得"""
        result = await db.execute(
            select(PipelineModel).where(PipelineModel.id == pipeline_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return Pipeline(
            id=str(model.id),
            name=model.name,
            description=model.description,
            components=[PipelineComponent(**comp) for comp in model.components],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create_pipeline(
        self, pipeline_request: PipelineCreateRequest, db: AsyncSession
    ) -> Pipeline:
        """新しいパイプラインを作成"""
        # PipelineComponentオブジェクトを辞書形式に変換してJSONシリアライズ可能にする
        components_dict = [
            component.dict() for component in pipeline_request.components
        ]

        pipeline_model = PipelineModel(
            name=pipeline_request.name,
            description=pipeline_request.description,
            components=components_dict,
        )

        db.add(pipeline_model)
        await db.commit()
        await db.refresh(pipeline_model)

        return Pipeline(
            id=str(pipeline_model.id),
            name=pipeline_model.name,
            description=pipeline_model.description,
            components=[
                PipelineComponent(**comp) for comp in pipeline_model.components
            ],
            created_at=pipeline_model.created_at,
            updated_at=pipeline_model.updated_at,
        )

    async def update_pipeline(
        self,
        pipeline_id: str,
        pipeline_request: PipelineUpdateRequest,
        db: AsyncSession,
    ) -> Optional[Pipeline]:
        """パイプラインを更新"""
        result = await db.execute(
            select(PipelineModel).where(PipelineModel.id == pipeline_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        if pipeline_request.name is not None:
            model.name = pipeline_request.name
        if pipeline_request.description is not None:
            model.description = pipeline_request.description
        if pipeline_request.components is not None:
            # PipelineComponentオブジェクトを辞書形式に変換
            model.components = [
                component.dict() for component in pipeline_request.components
            ]

        model.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(model)

        return Pipeline(
            id=str(model.id),
            name=model.name,
            description=model.description,
            components=[PipelineComponent(**comp) for comp in model.components],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def delete_pipeline(self, pipeline_id: str, db: AsyncSession) -> bool:
        """パイプラインを削除"""
        result = await db.execute(
            select(PipelineModel).where(PipelineModel.id == pipeline_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return False

        await db.delete(model)
        await db.commit()
        return True
