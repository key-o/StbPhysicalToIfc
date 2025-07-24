# ifcCreator/core/structural_geometry.py
"""
統合された構造要素幾何学計算モジュール
"""
import math
from typing import List, Literal
from dataclasses import dataclass
from common.geometry import Point3D


ElementType = Literal["BEAM", "COLUMN", "BRACE"]


@dataclass
class StructuralElementGeometry:
    """構造要素の幾何学的情報（梁・柱統合版）"""

    center: Point3D
    span: float  # length(梁) または height(柱)
    direction: List[float]
    reference_direction: List[float]
    element_type: ElementType

    @property
    def length(self) -> float:
        """梁の長さ（下位互換性のため）"""
        return self.span

    @property
    def height(self) -> float:
        """柱の高さ（下位互換性のため）"""
        return self.span


class StructuralGeometryCalculator:
    """構造要素の幾何学計算責務（梁・柱統合版）"""

    @staticmethod
    def calculate_beam_geometry(
        start: Point3D, end: Point3D
    ) -> StructuralElementGeometry:
        """梁の幾何学情報を計算"""
        geometry = StructuralGeometryCalculator._calculate_base_geometry(
            start, end, "BEAM"
        )

        # 梁固有の参照方向計算
        geometry.reference_direction = (
            StructuralGeometryCalculator._calculate_beam_reference_direction(
                geometry.direction
            )
        )

        return geometry

    @staticmethod
    def calculate_column_geometry(
        bottom: Point3D, top: Point3D
    ) -> StructuralElementGeometry:
        """柱の幾何学情報を計算"""
        geometry = StructuralGeometryCalculator._calculate_base_geometry(
            bottom, top, "COLUMN"
        )

        # 柱固有の参照方向計算
        geometry.reference_direction = (
            StructuralGeometryCalculator._calculate_column_reference_direction(
                geometry.direction
            )
        )

        return geometry

    @staticmethod
    def calculate_brace_geometry(
        start: Point3D, end: Point3D
    ) -> StructuralElementGeometry:
        """ブレースの幾何学情報を計算"""
        geometry = StructuralGeometryCalculator._calculate_base_geometry(
            start, end, "BRACE"
        )

        # ブレース固有の参照方向計算
        geometry.reference_direction = (
            StructuralGeometryCalculator._calculate_brace_reference_direction(
                geometry.direction
            )
        )

        return geometry

    @staticmethod
    def _calculate_base_geometry(
        start: Point3D, end: Point3D, element_type: ElementType
    ) -> StructuralElementGeometry:
        """基本幾何学情報を計算（共通ロジック）"""
        dx, dy, dz = end.x - start.x, end.y - start.y, end.z - start.z
        span = math.sqrt(dx * dx + dy * dy + dz * dz)

        center = Point3D(
            (start.x + end.x) / 2, (start.y + end.y) / 2, (start.z + end.z) / 2
        )

        # デフォルト方向の設定
        if element_type == "BEAM":
            default_direction = [1.0, 0.0, 0.0]  # 梁のデフォルト
        elif element_type == "BRACE":
            default_direction = [1.0, 0.0, 1.0]  # ブレースのデフォルト（斜め）
        else:  # COLUMN
            default_direction = [0.0, 0.0, 1.0]  # 柱のデフォルト

        direction = [dx / span, dy / span, dz / span] if span > 0 else default_direction

        return StructuralElementGeometry(
            center=center,
            span=span,
            direction=direction,
            reference_direction=[1.0, 0.0, 0.0],  # 一時的、後で更新
            element_type=element_type,
        )

    @staticmethod
    def _calculate_beam_reference_direction(beam_direction: List[float]) -> List[float]:
        """梁の参照方向を計算（断面の向きを決定）"""
        # 梁が鉛直（Z軸方向）の場合
        if abs(beam_direction[0]) < 1e-6 and abs(beam_direction[1]) < 1e-6:
            return [1.0, 0.0, 0.0]

        # 水平梁の場合、常にZ軸を断面のY軸とするための参照方向を計算
        ref_x = -beam_direction[1]
        ref_y = beam_direction[0]
        ref_z = 0.0

        # ベクトルの正規化
        length = math.sqrt(ref_x * ref_x + ref_y * ref_y + ref_z * ref_z)
        if length > 1e-6:
            return [ref_x / length, ref_y / length, ref_z / length]
        else:
            return [1.0, 0.0, 0.0]

    @staticmethod
    def _calculate_column_reference_direction(
        column_direction: List[float],
    ) -> List[float]:
        """柱の参照方向を計算（断面の向きを決定）"""
        # 鉛直柱（Z軸方向）の場合
        if abs(column_direction[2]) > 0.9:  # ほぼ鉛直
            return [1.0, 0.0, 0.0]

        # 傾斜柱の場合、柱軸と重力方向に垂直な方向を求める
        ref_x = -column_direction[1]
        ref_y = column_direction[0]
        ref_z = 0.0

        # ベクトルの正規化
        length = math.sqrt(ref_x * ref_x + ref_y * ref_y + ref_z * ref_z)
        if length > 1e-6:
            return [ref_x / length, ref_y / length, ref_z / length]
        else:
            return [1.0, 0.0, 0.0]

    @staticmethod
    def _calculate_brace_reference_direction(
        brace_direction: List[float],
    ) -> List[float]:
        """ブレースの参照方向を計算（断面の向きを決定）"""
        # ブレースは一般的に斜め要素なので、重力方向（Z軸）に垂直な
        # 最も近い水平方向を参照方向とする

        # ブレースが完全に水平の場合
        if abs(brace_direction[2]) < 1e-6:
            # Y軸方向を参照とする
            return [0.0, 1.0, 0.0]

        # ブレースが完全に鉛直の場合
        if abs(brace_direction[0]) < 1e-6 and abs(brace_direction[1]) < 1e-6:
            return [1.0, 0.0, 0.0]

        # 一般的な斜めブレースの場合、ブレース軸と鉛直方向に垂直な
        # 水平方向を計算
        ref_x = -brace_direction[1]
        ref_y = brace_direction[0]
        ref_z = 0.0

        # ベクトルの正規化
        length = math.sqrt(ref_x * ref_x + ref_y * ref_y + ref_z * ref_z)
        if length > 1e-6:
            return [ref_x / length, ref_y / length, ref_z / length]
        else:
            return [1.0, 0.0, 0.0]
