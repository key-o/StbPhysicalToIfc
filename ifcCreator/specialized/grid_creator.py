"""IfcGrid を生成するクリエータ"""

from typing import List, Dict, Any, Optional
from ..creators.base_creator import StructuralElementCreatorBase
# Simplified imports for v2.2.0
# from ..geometry.unified_geometry_builder import UnifiedGeometryBuilder  # Not available
# from ..services.element_type_manager import ElementTypeManager  # Not available
# from ..geometry.structural_geometry import StructuralGeometryCalculator  # Available
# from ..utils.profile_factory_base import ProfileFactoryBase  # Not available
# from ..utils.property_manager_base import PropertyManagerBase  # Not available
from common.geometry import Point3D
from common.guid_utils import create_ifc_guid
import logging

logger = logging.getLogger(__name__)


class GridPropertyManager:
    """通芯用プロパティマネージャー（簡素化実装）"""

    def get_section_properties(self, section, section_end=None, is_tapered=False):
        """通芯にはセクションプロパティは不要"""
        return {}

    def _get_rectangle_properties(self, section):
        """矩形断面プロパティ（通芯では使用しない）"""
        return {}

    def _get_circle_properties(self, section):
        """円形断面プロパティ（通芯では使用しない）"""
        return {}

    def _get_h_properties(self, section):
        """H形断面プロパティ（通芯では使用しない）"""
        return {}


class IFCGridCreator(StructuralElementCreatorBase):
    """IfcGrid作成クラス"""
    
    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """通芯要素を作成（BaseElementCreatorの抽象メソッド実装）"""
        # 簡易実装 - 実際の通芯作成はcreate_grid_from_axes_groupsで行う
        return None

    def __init__(self, project_builder=None):
        # v2.2.0: Simplified initialization
        super().__init__(project_builder)
        self.logger = logger

    def create_grid_from_axes_groups(self, axes_groups: List[Dict]) -> Optional[Any]:
        """通芯グループからIfcGridを作成

        Args:
            axes_groups: 通芯グループのリスト

        Returns:
            作成されたIfcGridオブジェクト
        """
        try:
            logger.info(
                "create_grid_from_axes_groups開始: %d個のグループ", len(axes_groups)
            )

            if not axes_groups:
                logger.warning("通芯グループが空です")
                return None

            # v2.2.0: Simplified - project_builder handles IFC file access
            if not self.project_builder or not self.project_builder.file:
                logger.warning("プロジェクトビルダーまたはIFCファイルが設定されていません")
                return None
            else:
                logger.info("プロジェクト構造を使用")
        except Exception as e:
            logger.error("初期化段階でエラー: %s", e)
            import traceback

            logger.error("トレースバック: %s", traceback.format_exc())
            return None

        try:
            ifc_file = self.project_builder.file
            assert ifc_file is not None, "IFC file not initialized"

            # すべての軸を収集
            all_u_axes = []  # U方向（通常X方向）
            all_v_axes = []  # V方向（通常Y方向）

            logger.info("軸収集を開始")

            for group in axes_groups:
                group_name = group.get("group_name", "Unknown")
                angle = group.get("angle", 0)
                axes = group.get("axes", [])

                for axis_data in axes:
                    axis_name = axis_data.get("name", "Unknown")
                    start_point = axis_data.get("start_point")
                    end_point = axis_data.get("end_point")

                    if not start_point or not end_point:
                        logger.warning("通芯 %s の座標が不正です", axis_name)
                        continue

                    # IfcGridAxisを作成
                    grid_axis = self._create_grid_axis(
                        axis_name, start_point, end_point
                    )

                    if grid_axis:
                        # グループ名に基づいて方向を決定
                        if (
                            group_name.upper().startswith("X")
                            or "X" in group_name.upper()
                        ):
                            all_u_axes.append(grid_axis)
                        elif (
                            group_name.upper().startswith("Y")
                            or "Y" in group_name.upper()
                        ):
                            all_v_axes.append(grid_axis)
                        else:
                            # 角度や座標から判断
                            if abs(angle % 180) < 45 or abs(angle % 180) > 135:
                                all_u_axes.append(grid_axis)  # 主にX方向
                            else:
                                all_v_axes.append(grid_axis)  # 主にY方向

            if not all_u_axes and not all_v_axes:
                logger.warning("有効な通芯軸が見つかりません")
                return None

            # IfcGridを作成
            grid = self._create_ifc_grid(all_u_axes, all_v_axes)

            logger.info(
                "IfcGrid作成完了: U軸=%d本, V軸=%d本", len(all_u_axes), len(all_v_axes)
            )
            return grid
        except Exception as e:
            logger.error("IfcGrid作成中にエラー: %s", e)
            import traceback

            logger.error("トレースバック: %s", traceback.format_exc())
            return None

    def _create_grid_axis(
        self, axis_name: str, start_point: Dict, end_point: Dict
    ) -> Optional[Any]:
        """IfcGridAxisを作成

        Args:
            axis_name: 軸名
            start_point: 開始点座標 {"x": float, "y": float, "z": float}
            end_point: 終了点座標 {"x": float, "y": float, "z": float}

        Returns:
            作成されたIfcGridAxisオブジェクト
        """
        ifc_file = self.project_builder.file

        try:
            # 開始点と終了点のIfcCartesianPointを作成
            start_ifc_point = ifc_file.createIfcCartesianPoint(
                [
                    float(start_point["x"]),
                    float(start_point["y"]),
                    float(start_point["z"]),
                ]
            )

            end_ifc_point = ifc_file.createIfcCartesianPoint(
                [float(end_point["x"]), float(end_point["y"]), float(end_point["z"])]
            )

            # IfcLineを作成
            direction_vector = [
                float(end_point["x"] - start_point["x"]),
                float(end_point["y"] - start_point["y"]),
                float(end_point["z"] - start_point["z"]),
            ]

            # 方向ベクトルを正規化
            length = sum(v**2 for v in direction_vector) ** 0.5
            if length > 0:
                direction_vector = [v / length for v in direction_vector]
            else:
                logger.warning("通芯 %s の長さが0です", axis_name)
                return None

            direction = ifc_file.createIfcDirection(direction_vector)
            vector = ifc_file.createIfcVector(direction, length)
            line = ifc_file.createIfcLine(start_ifc_point, vector)

            # IfcGridAxisを作成
            grid_axis = ifc_file.createIfcGridAxis(
                AxisTag=axis_name, AxisCurve=line, SameSense=True
            )

            logger.debug("IfcGridAxis作成: %s", axis_name)
            return grid_axis

        except Exception as e:
            logger.error("IfcGridAxis作成エラー (%s): %s", axis_name, e)
            return None

    def _create_ifc_grid(self, u_axes: List[Any], v_axes: List[Any]) -> Any:
        """IfcGridオブジェクトを作成

        Args:
            u_axes: U方向の軸リスト
            v_axes: V方向の軸リスト

        Returns:
            作成されたIfcGridオブジェクト
        """
        ifc_file = self.project_builder.file

        # IfcGridを作成
        grid = ifc_file.createIfcGrid(
            GlobalId=create_ifc_guid(),
            OwnerHistory=self.project_builder.owner_history,
            Name="構造通芯",
            Description="ST-Bridgeから変換された構造通芯",
            UAxes=u_axes if u_axes else None,
            VAxes=v_axes if v_axes else None,
            WAxes=None,  # 3D軸は今回は対応しない
        )

        # 配置情報を設定
        placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=None,  # ワールド座標系
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint([0.0, 0.0, 0.0])
            ),
        )
        grid.ObjectPlacement = placement

        # 空間構造に追加（Buildingレベルに配置）
        logger.info("プロジェクトビルダーの空間構造確認:")
        logger.info("  building: %s", getattr(self.project_builder, "building", None))
        logger.info("  site: %s", getattr(self.project_builder, "site", None))
        logger.info("  storey: %s", getattr(self.project_builder, "storey", None))

        relating_structure = None
        if hasattr(self.project_builder, "building") and self.project_builder.building:
            relating_structure = self.project_builder.building
            logger.info("通芯をBuildingレベルに配置")
        elif hasattr(self.project_builder, "site") and self.project_builder.site:
            relating_structure = self.project_builder.site
            logger.info("通芯をSiteレベルに配置")
        elif hasattr(self.project_builder, "storey") and self.project_builder.storey:
            relating_structure = self.project_builder.storey
            logger.info("通芯をStoreyレベルに配置")

        if relating_structure:
            rel_contains = ifc_file.createIfcRelContainedInSpatialStructure(
                GlobalId=create_ifc_guid(),
                OwnerHistory=self.project_builder.owner_history,
                RelatingStructure=relating_structure,
                RelatedElements=[grid],
            )
            logger.info("通芯の空間構造への関連付け完了: %s", relating_structure)
        else:
            logger.warning(
                "適切な空間構造が見つからないため、通芯の関連付けをスキップします"
            )

        return grid


# ===== 通芯定義処理クラス =====
class GridDefinitionProcessor:
    """通芯定義辞書を検証・変換するクラス"""

    def process(self, axes_groups: List[Dict]) -> List[Dict]:
        """通芯グループリストを処理"""
        import json

        logger.debug("通芯定義処理開始:")
        logger.debug("通芯グループ数: %d", len(axes_groups))

        processed_groups = []
        for group in axes_groups:
            processed_group = self._process_single_group(group)
            if processed_group:
                processed_groups.append(processed_group)

        logger.debug("処理後通芯グループ数: %d", len(processed_groups))
        return processed_groups

    def _process_single_group(self, group: Dict) -> Optional[Dict]:
        """個別の通芯グループを処理"""
        group_name = group.get("group_name", "Unknown")
        axes = group.get("axes", [])

        if not axes:
            logger.warning("通芯グループ %s に軸がありません", group_name)
            return None

        processed_axes = []
        for axis in axes:
            if self._validate_axis(axis):
                processed_axes.append(axis)

        if not processed_axes:
            logger.warning("通芯グループ %s に有効な軸がありません", group_name)
            return None

        return {
            "group_name": group_name,
            "origin_x": group.get("origin_x", 0),
            "origin_y": group.get("origin_y", 0),
            "angle": group.get("angle", 0),
            "axes": processed_axes,
        }

    def _validate_axis(self, axis: Dict) -> bool:
        """通芯軸の検証"""
        required_fields = ["name", "start_point", "end_point"]

        for field in required_fields:
            if field not in axis:
                logger.warning("通芯軸に必須フィールド %s がありません", field)
                return False

        # 座標の検証
        for point_name in ["start_point", "end_point"]:
            point = axis[point_name]
            if not isinstance(point, dict):
                logger.warning("通芯軸の %s が辞書形式ではありません", point_name)
                return False

            for coord in ["x", "y", "z"]:
                if coord not in point:
                    logger.warning(
                        "通芯軸の %s に座標 %s がありません", point_name, coord
                    )
                    return False

        return True
