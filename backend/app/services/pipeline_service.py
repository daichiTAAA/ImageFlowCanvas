from typing import List, Optional
from app.models.pipeline import Pipeline, PipelineCreateRequest, PipelineUpdateRequest
from datetime import datetime

class PipelineService:
    def __init__(self):
        # インメモリストレージ（本番環境ではデータベースを使用）
        self.pipelines = {}
    
    async def get_all_pipelines(self) -> List[Pipeline]:
        """全パイプラインを取得"""
        return list(self.pipelines.values())
    
    async def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """特定のパイプラインを取得"""
        return self.pipelines.get(pipeline_id)
    
    async def create_pipeline(self, pipeline_request: PipelineCreateRequest) -> Pipeline:
        """新しいパイプラインを作成"""
        pipeline = Pipeline(
            name=pipeline_request.name,
            description=pipeline_request.description,
            components=pipeline_request.components
        )
        self.pipelines[pipeline.id] = pipeline
        return pipeline
    
    async def update_pipeline(self, pipeline_id: str, pipeline_request: PipelineUpdateRequest) -> Optional[Pipeline]:
        """パイプラインを更新"""
        pipeline = self.pipelines.get(pipeline_id)
        if not pipeline:
            return None
        
        if pipeline_request.name is not None:
            pipeline.name = pipeline_request.name
        if pipeline_request.description is not None:
            pipeline.description = pipeline_request.description
        if pipeline_request.components is not None:
            pipeline.components = pipeline_request.components
        
        pipeline.updated_at = datetime.utcnow()
        return pipeline
    
    async def delete_pipeline(self, pipeline_id: str) -> bool:
        """パイプラインを削除"""
        if pipeline_id in self.pipelines:
            del self.pipelines[pipeline_id]
            return True
        return False