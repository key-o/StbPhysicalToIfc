"""Geometry Service

統一ジオメトリ構築サービス
v2.2.0: 簡素化された統一実装 + Phase1強化（ジオメトリ配置精度向上）
"""

from typing import List, Optional, Dict, Any, Union
import logging

# v2.2.0: 統合アーキテクチャ - 簡素化されたジオメトリ構築
from ..geometry.geometry_builder import GeometryBuilder
from ..geometry.structural_geometry import (
    StructuralGeometryCalculator,
    StructuralElementGeometry,
)
from common.geometry import Point3D

logger = logging.getLogger(__name__)


class GeometryService:
    """ジオメトリ構築の統一サービス

    v2.2.0: 簡素化された統一実装
    """

    def __init__(self, ifc_file=None, model_context=None):
        """GeometryServiceの初期化

        Args:
            ifc_file: IFCファイルオブジェクト（オプション）
            model_context: モデルコンテキスト（オプション）
        """
        self.file = ifc_file
        self.model_context = model_context
        self.geometry_builder = GeometryBuilder()

    def create_linear_geometry(
        self, start_point: Point3D, end_point: Point3D, profile_start, profile_end=None
    ) -> Dict[str, Any]:
        """線要素ジオメトリを作成

        Args:
            start_point: 開始点
            end_point: 終了点
            profile_start: 開始プロファイル
            profile_end: 終了プロファイル（変断面用）

        Returns:
            ジオメトリ情報辞書
        """
        # v2.2.0: 簡素化されたジオメトリ作成
        return {
            "type": "linear",
            "start_point": start_point,
            "end_point": end_point,
            "profile_start": profile_start,
            "profile_end": profile_end,
            "created_by": "GeometryService v2.2.0",
        }

    def create_planar_geometry(
        self, outline_points: List[Point3D], thickness: float = 0.0
    ) -> Dict[str, Any]:
        """面要素ジオメトリを作成

        Args:
            outline_points: 輪郭点リスト
            thickness: 厚さ

        Returns:
            ジオメトリ情報辞書
        """
        # v2.2.0: 簡素化されたジオメトリ作成
        return {
            "type": "planar",
            "outline_points": outline_points,
            "thickness": thickness,
            "created_by": "GeometryService v2.2.0",
        }

    def create_placement(self, origin: Point3D, direction=None, ref_direction=None):
        """配置情報を作成

        Args:
            origin: 原点
            direction: 方向ベクトル
            ref_direction: 参照方向ベクトル

        Returns:
            配置情報（プレースホルダー）
        """
        return {
            "origin": origin,
            "direction": direction,
            "ref_direction": ref_direction,
            "created_by": "GeometryService v2.2.0",
        }

    def create_structural_placement(
        self, start_point: Point3D, end_point: Point3D, element_type: str = "BEAM"
    ) -> Dict[str, Any]:
        """構造要素用の精密配置計算

        Phase 1強化: StructuralGeometryCalculatorを使用した精密配置

        Args:
            start_point: 開始点
            end_point: 終了点
            element_type: 要素タイプ ("BEAM", "COLUMN", "BRACE")

        Returns:
            精密配置情報
        """
        # StructuralGeometryCalculatorを使用して精密計算
        if element_type.upper() == "BEAM":
            geometry = StructuralGeometryCalculator.calculate_beam_geometry(
                start_point, end_point
            )
        elif element_type.upper() == "COLUMN":
            geometry = StructuralGeometryCalculator.calculate_column_geometry(
                start_point, end_point
            )
        elif element_type.upper() == "BRACE":
            geometry = StructuralGeometryCalculator.calculate_brace_geometry(
                start_point, end_point
            )
        else:
            # フォールバック: デフォルト梁計算
            geometry = StructuralGeometryCalculator.calculate_beam_geometry(
                start_point, end_point
            )

        return {
            "origin": geometry.center,
            "direction": geometry.direction,
            "ref_direction": geometry.reference_direction,
            "length": geometry.span,
            "element_type": geometry.element_type,
            "created_by": "GeometryService v2.2.0 Phase1-Enhanced",
        }

    def get_geometry_builder(self, element_type: str):
        """要素タイプ別ジオメトリビルダーを取得

        Args:
            element_type: 要素タイプ

        Returns:
            適切なジオメトリビルダー
        """
        return self.geometry_builder
