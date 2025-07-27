"""
検査実行サービス - AI パイプライン統合
"""

import uuid
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.inspection import InspectionItemExecution, InspectionItem
from app.schemas.inspection import AIResult, Detection, BoundingBox, JudgmentResult
from app.services.grpc_pipeline_executor import GRPCPipelineExecutor

# from app.services.file_service import FileService  # 使用しない

logger = logging.getLogger(__name__)


class InspectionExecutor:
    """検査実行エンジン"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pipeline_executor = GRPCPipelineExecutor()
        self.file_storage = FileStorageService()

    async def execute_ai_inspection(
        self,
        item_execution: InspectionItemExecution,
        image_data: bytes,
        image_format: str = "image/jpeg",
    ) -> Optional[AIResult]:
        """AI検査を実行"""
        try:
            # 検査項目を取得
            if not item_execution.item:
                item = await self.db.execute(
                    select(InspectionItem).where(
                        InspectionItem.id == item_execution.item_id
                    )
                )
                item = item.scalar_one_or_none()
                if not item:
                    raise ValueError(
                        f"Inspection item not found: {item_execution.item_id}"
                    )
                item_execution.item = item

            # 画像を保存
            image_file_id = await self._save_image(image_data, image_format)
            item_execution.image_file_id = image_file_id

            # パイプラインIDがない場合はスキップ
            if not item_execution.item.pipeline_id:
                logger.warning(
                    f"No pipeline defined for inspection item: {item_execution.item_id}"
                )
                return None

            # パイプライン実行
            pipeline_result = await self._execute_pipeline(
                pipeline_id=str(item_execution.item.pipeline_id),
                image_data=image_data,
                pipeline_params=item_execution.item.pipeline_params or {},
            )

            if not pipeline_result:
                logger.warning(
                    f"Pipeline execution returned no result for item: {item_execution.item_id}"
                )
                return None

            # AI結果をパース
            ai_result = self._parse_pipeline_result(
                pipeline_result, item_execution.item
            )

            # パイプライン実行IDを保存
            if hasattr(pipeline_result, "execution_id"):
                item_execution.pipeline_execution_id = pipeline_result.execution_id

            logger.info(f"AI inspection completed for item: {item_execution.item_id}")
            return ai_result

        except Exception as e:
            logger.error(f"Failed to execute AI inspection: {e}")
            raise

    async def _save_image(self, image_data: bytes, image_format: str) -> uuid.UUID:
        """画像をファイルストレージに保存"""
        try:
            # ファイル拡張子を決定
            extension = "jpg"
            if "png" in image_format.lower():
                extension = "png"
            elif "gif" in image_format.lower():
                extension = "gif"

            # ファイル名を生成
            file_id = uuid.uuid4()
            filename = f"inspection_{file_id}.{extension}"

            # ファイルストレージに保存
            await self.file_storage.save_file(
                file_id=file_id,
                filename=filename,
                content=image_data,
                content_type=image_format,
            )

            return file_id

        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise

    async def _execute_pipeline(
        self, pipeline_id: str, image_data: bytes, pipeline_params: Dict[str, Any]
    ) -> Optional[Any]:
        """パイプラインを実行"""
        try:
            # GRPCパイプライン実行器を使用
            result = await self.pipeline_executor.execute_pipeline_direct(
                pipeline_id=pipeline_id,
                image_data=image_data,
                execution_params=pipeline_params,
            )

            return result

        except Exception as e:
            logger.error(f"Failed to execute pipeline {pipeline_id}: {e}")
            raise

    def _parse_pipeline_result(
        self, pipeline_result: Any, inspection_item: InspectionItem
    ) -> AIResult:
        """パイプライン実行結果をAI結果に変換"""
        try:
            # パイプライン結果の構造を分析
            if hasattr(pipeline_result, "result") and hasattr(
                pipeline_result.result, "output_data"
            ):
                # 標準的なパイプライン結果形式
                output_data = pipeline_result.result.output_data
                processing_time = (
                    getattr(pipeline_result.result, "processing_time_seconds", 0) * 1000
                )
            else:
                # 直接的な結果形式
                output_data = pipeline_result
                processing_time = 0

            # AI検知結果を抽出
            detections = []
            measurements = {}
            confidence_score = 0.0
            explanation = ""

            if isinstance(output_data, dict):
                # AI検知結果がある場合
                if "detections" in output_data:
                    detections = self._parse_detections(output_data["detections"])

                # 測定値がある場合
                if "measurements" in output_data:
                    measurements = output_data["measurements"]

                # 信頼度スコア
                if "confidence" in output_data:
                    confidence_score = float(output_data["confidence"])
                elif detections:
                    # 検出結果から平均信頼度を計算
                    confidence_score = sum(d.confidence for d in detections) / len(
                        detections
                    )

                # 説明
                if "explanation" in output_data:
                    explanation = output_data["explanation"]

            # 検査基準に基づく判定
            judgment = self._evaluate_judgment(
                detections=detections,
                measurements=measurements,
                confidence_score=confidence_score,
                inspection_item=inspection_item,
            )

            return AIResult(
                judgment=judgment,
                confidence_score=confidence_score,
                detections=detections,
                measurements=measurements,
                explanation=explanation,
                processing_time_ms=int(processing_time),
            )

        except Exception as e:
            logger.error(f"Failed to parse pipeline result: {e}")
            # デフォルト結果を返す
            return AIResult(
                judgment=JudgmentResult.INCONCLUSIVE,
                confidence_score=0.0,
                detections=[],
                measurements={},
                explanation=f"Failed to parse result: {str(e)}",
                processing_time_ms=0,
            )

    def _parse_detections(self, detections_data: Any) -> List[Detection]:
        """検出結果をパース"""
        detections = []

        try:
            if isinstance(detections_data, list):
                for det_data in detections_data:
                    if isinstance(det_data, dict):
                        # バウンディングボックスをパース
                        bbox_data = det_data.get("bbox", {})
                        bbox = BoundingBox(
                            x1=float(bbox_data.get("x1", 0)),
                            y1=float(bbox_data.get("y1", 0)),
                            x2=float(bbox_data.get("x2", 0)),
                            y2=float(bbox_data.get("y2", 0)),
                        )

                        detection = Detection(
                            class_name=det_data.get("class_name", "unknown"),
                            confidence=float(det_data.get("confidence", 0.0)),
                            bbox=bbox,
                            attributes=det_data.get("attributes", {}),
                        )
                        detections.append(detection)
        except Exception as e:
            logger.warning(f"Failed to parse detections: {e}")

        return detections

    def _evaluate_judgment(
        self,
        detections: List[Detection],
        measurements: Dict[str, float],
        confidence_score: float,
        inspection_item: InspectionItem,
    ) -> JudgmentResult:
        """検査基準に基づいて判定を行う"""
        try:
            # 検査基準がない場合は検出結果に基づいて判定
            if not inspection_item.criteria:
                # 検出がない場合はOK、ある場合は信頼度で判定
                if not detections:
                    return JudgmentResult.OK

                # 高い信頼度の検出がある場合はNG
                high_confidence_detections = [
                    d for d in detections if d.confidence > 0.7
                ]
                if high_confidence_detections:
                    return JudgmentResult.NG

                # 中程度の信頼度の場合は確認待ち
                if any(d.confidence > 0.3 for d in detections):
                    return JudgmentResult.PENDING_REVIEW

                return JudgmentResult.OK

            # 検査基準に基づく判定
            criteria_spec = inspection_item.criteria.spec

            if criteria_spec.get("binary"):
                # 二値判定
                binary_spec = criteria_spec["binary"]
                expected = binary_spec.get("expected_value", True)
                has_detections = len(detections) > 0

                if expected == has_detections:
                    return JudgmentResult.OK
                else:
                    return JudgmentResult.NG

            elif criteria_spec.get("threshold"):
                # 閾値判定
                threshold_spec = criteria_spec["threshold"]
                threshold = threshold_spec.get("threshold", 0.5)
                operator = threshold_spec.get("operator", "GREATER_THAN")

                value = confidence_score
                if measurements and "main_value" in measurements:
                    value = measurements["main_value"]

                if operator == "GREATER_THAN":
                    return JudgmentResult.OK if value > threshold else JudgmentResult.NG
                elif operator == "GREATER_THAN_OR_EQUAL":
                    return (
                        JudgmentResult.OK if value >= threshold else JudgmentResult.NG
                    )
                elif operator == "LESS_THAN":
                    return JudgmentResult.OK if value < threshold else JudgmentResult.NG
                elif operator == "LESS_THAN_OR_EQUAL":
                    return (
                        JudgmentResult.OK if value <= threshold else JudgmentResult.NG
                    )
                elif operator == "EQUAL":
                    return (
                        JudgmentResult.OK
                        if abs(value - threshold) < 0.01
                        else JudgmentResult.NG
                    )
                else:
                    return (
                        JudgmentResult.OK
                        if abs(value - threshold) >= 0.01
                        else JudgmentResult.NG
                    )

            elif criteria_spec.get("numerical"):
                # 数値範囲判定
                numerical_spec = criteria_spec["numerical"]
                min_value = numerical_spec.get("min_value", float("-inf"))
                max_value = numerical_spec.get("max_value", float("inf"))

                value = confidence_score
                if measurements and "main_value" in measurements:
                    value = measurements["main_value"]

                if min_value <= value <= max_value:
                    return JudgmentResult.OK
                else:
                    return JudgmentResult.NG

            elif criteria_spec.get("categorical"):
                # カテゴリ分類判定
                categorical_spec = criteria_spec["categorical"]
                allowed_categories = categorical_spec.get("allowed_categories", [])

                detected_categories = [d.class_name for d in detections]

                # 許可されたカテゴリのみが検出された場合はOK
                if all(cat in allowed_categories for cat in detected_categories):
                    return JudgmentResult.OK
                else:
                    return JudgmentResult.NG

            # デフォルト: 判定不能
            return JudgmentResult.INCONCLUSIVE

        except Exception as e:
            logger.error(f"Failed to evaluate judgment: {e}")
            return JudgmentResult.INCONCLUSIVE


class FileStorageService:
    """ファイルストレージサービス（簡易実装）"""

    async def save_file(
        self, file_id: uuid.UUID, filename: str, content: bytes, content_type: str
    ) -> None:
        """ファイルを保存（実際の実装では MinIO などを使用）"""
        # TODO: 実際の実装では MinIO や S3 にファイルを保存
        logger.info(f"Saving file {filename} ({len(content)} bytes) with ID {file_id}")
        pass
