"""壁の開口作成専用サービス

壁の開口作成責任を分離し、IFCWallCreatorの複雑度を削減
"""

import logging
from typing import List, Dict, Optional
from ..utils.structural_section import StructuralSection
from ifcCreator.unified_profile_factory import (
    UnifiedProfileFactory,
    UnifiedProfileConfig,
)
from common.guid_utils import create_ifc_guid


class WallOpeningService:
    """壁の開口作成専用サービス"""

    def __init__(
        self, ifc_file, project_builder=None, logger: Optional[logging.Logger] = None
    ):
        self.file = ifc_file
        self.project_builder = project_builder
        self.logger = logger or logging.getLogger(__name__)
        self.model_context = self._get_model_context()

    def create_wall_openings(
        self,
        wall,
        openings: List[Dict],
        section: StructuralSection,
        wall_direction: Optional[Dict] = None,
    ):
        """壁の開口要素を作成"""
        if not self.file:
            return

        for opening_data in openings:
            try:
                self._create_single_opening(wall, opening_data, section, wall_direction)
            except Exception as e:
                opening_id = opening_data.get("id", "Unknown")
                self.logger.error(f"開口 {opening_id} の作成に失敗: {e}")

    def _create_single_opening(
        self,
        wall,
        opening_data: Dict,
        section: StructuralSection,
        wall_direction: Optional[Dict] = None,
    ):
        """単一の開口を作成"""
        # 開口パラメータの取得
        dimensions = opening_data.get("dimensions", {})
        relative_position = opening_data.get("relative_position", {})
        opening_id = opening_data.get("id", "Unknown")

        # 開口サイズ
        width = float(dimensions.get("width", 1000))
        height = float(dimensions.get("height", 2000))
        wall_thickness = getattr(section, "thickness", 300.0)

        # 開口プロファイル作成（UnifiedProfileFactoryを使用）
        config = UnifiedProfileConfig(
            section_type="RECTANGLE",
            name=f"Opening_{opening_id}",
            width=width,
            height=height,
        )
        opening_profile = UnifiedProfileFactory.create_profile(self.file, config)

        # 開口位置計算
        local_x, local_y, local_z = self._calculate_opening_position(
            relative_position, section, width, height
        )

        # 開口配置作成
        opening_placement = self._create_opening_placement(
            wall, local_x, local_y, local_z
        )

        # 開口ジオメトリ作成
        opening_solid = self._create_opening_solid(opening_profile, wall_thickness)

        # 開口要素作成
        opening_element = self._create_opening_element(
            opening_id, opening_placement, opening_solid
        )

        # 壁との関係作成
        self._create_voiding_relationship(wall, opening_element, opening_id)

        self.logger.debug(
            f"開口 {opening_id} を作成: 幅={width}mm, 高さ={height}mm, "
            f"位置=({local_x:.1f}, {local_y:.1f}, {local_z:.1f})"
        )

    def _calculate_opening_position(
        self,
        relative_position: Dict,
        section: StructuralSection,
        width: float,
        height: float,
    ) -> tuple[float, float, float]:
        """開口の位置を計算"""
        rel_x = float(relative_position.get("x", 0))
        rel_z = float(relative_position.get("y", 0))

        wall_length = getattr(section, "length", 6000.0)
        wall_height = getattr(section, "height", 4500.0)

        # STB座標からIFC中心基準座標への変換
        center_offset_x = rel_x - wall_length / 2.0
        center_offset_z = rel_z - wall_height / 2.0

        # 開口の中心位置
        local_x = center_offset_x + width / 2.0
        local_y = center_offset_z + height / 2.0
        local_z = 0.0

        return local_x, local_y, local_z

    def _create_opening_placement(
        self, wall, local_x: float, local_y: float, local_z: float
    ):
        """開口の配置を作成"""
        opening_location = self.file.createIfcCartesianPoint(
            [local_x, local_y, local_z]
        )
        opening_axis = self.file.createIfcDirection([0.0, 0.0, 1.0])
        opening_ref = self.file.createIfcDirection([1.0, 0.0, 0.0])

        opening_placement_3d = self.file.createIfcAxis2Placement3D(
            Location=opening_location,
            Axis=opening_axis,
            RefDirection=opening_ref,
        )

        return self.file.createIfcLocalPlacement(
            PlacementRelTo=wall.ObjectPlacement,
            RelativePlacement=opening_placement_3d,
        )

    def _create_opening_solid(self, opening_profile, wall_thickness: float):
        """開口のソリッドジオメトリを作成"""
        epsilon = 1.0  # クリアランス

        solid_placement = self.file.createIfcAxis2Placement3D(
            Location=self.file.createIfcCartesianPoint(
                [0.0, 0.0, -wall_thickness / 2.0 - epsilon]
            )
        )

        extrusion_direction = self.file.createIfcDirection([0.0, 0.0, 1.0])

        return self.file.createIfcExtrudedAreaSolid(
            SweptArea=opening_profile,
            Position=solid_placement,
            ExtrudedDirection=extrusion_direction,
            Depth=wall_thickness + (2 * epsilon),
        )

    def _create_opening_element(self, opening_id: str, placement, solid):
        """開口要素を作成"""
        opening_shape_rep = self.file.createIfcShapeRepresentation(
            ContextOfItems=self.model_context,  # 適切なモデルコンテキストを設定
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[solid],
        )

        opening_product_shape = self.file.createIfcProductDefinitionShape(
            Representations=[opening_shape_rep]
        )

        return self.file.createIfcOpeningElement(
            GlobalId=create_ifc_guid(),
            Name=f"Opening_{opening_id}",
            Description=f"Wall opening from STB id={opening_id}",
            ObjectPlacement=placement,
            Representation=opening_product_shape,
        )

    def _create_voiding_relationship(self, wall, opening_element, opening_id: str):
        """壁と開口の関係を作成"""
        return self.file.createIfcRelVoidsElement(
            GlobalId=create_ifc_guid(),
            Name=f"WallVoiding_{opening_id}",
            Description=f"Voiding relationship for opening {opening_id}",
            RelatingBuildingElement=wall,
            RelatedOpeningElement=opening_element,
        )

    def _get_model_context(self):
        """モデルコンテキストを取得"""
        # まずproject_builderから取得を試行
        if self.project_builder and hasattr(self.project_builder, "model_context"):
            return self.project_builder.model_context

        # project_builderがない場合はIFCファイルから検索
        if not self.file:
            return None

        try:
            # IfcGeometricRepresentationContextを検索
            contexts = self.file.by_type("IfcGeometricRepresentationContext")
            if contexts:
                # Model contextsを探す
                for context in contexts:
                    if (
                        hasattr(context, "ContextType")
                        and context.ContextType == "Model"
                    ):
                        return context
                # Modelがなければ最初のcontextを使用
                return contexts[0]
        except Exception as e:
            self.logger.warning(f"モデルコンテキスト取得エラー: {e}")

        return None
