"""Slab Creator

v2.2.0 統合スラブ作成クラス
"""

from typing import Optional, Any, Dict, List
from .base_creator import PlanarElementCreator
from ..utils.structural_section import StructuralSection
from ..utils.validator import Validator
from common.geometry import Point3D
from exceptions.custom_errors import ParameterValidationError, GeometryValidationError
import logging

logger = logging.getLogger(__name__)


class SlabCreator(PlanarElementCreator):
    """統合スラブ作成クラス"""

    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "slab"
        self.validator = Validator()

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """スラブ要素を作成"""
        try:
            # パラメータ検証
            try:
                self.validator.validate_slab_definition(definition)
            except ValueError as e:
                slab_name = definition.get("name", "不明なスラブ")
                raise ParameterValidationError("スラブ", slab_name, str(e)) from e
            
            # 定義から必要パラメータを抽出
            corner_nodes = definition.get("corner_nodes")
            center_point = definition.get("center_point")

            # STBパーサーの出力形式に対応（section辞書からStructuralSectionを作成）
            section_data = definition.get("section")
            slab_section = None
            if section_data:
                # 重複を避けるため、name と section_type を除いた辞書を作成
                other_properties = {
                    k: v
                    for k, v in section_data.items()
                    if k not in ["stb_name", "section_type"]
                }
                slab_section = StructuralSection(
                    name=section_data.get("stb_name", ""),
                    section_type=section_data.get("section_type", ""),
                    **other_properties,
                )

            slab_name = definition.get("name", "Slab")
            slab_tag = definition.get("tag", "SL001")
            stb_guid = definition.get("stb_guid")

            # Point3Dオブジェクトのリストを作成
            corner_points = []
            if corner_nodes and isinstance(corner_nodes, list):
                for node in corner_nodes:
                    if isinstance(node, dict):
                        corner_points.append(Point3D(node["x"], node["y"], node["z"]))

            if center_point and isinstance(center_point, dict):
                center_point = Point3D(
                    center_point["x"], center_point["y"], center_point["z"]
                )

            if not all([corner_points, slab_section]):
                self.logger.error(
                    f"必須パラメータが不足しています: corner_points={len(corner_points) if corner_points else 0}, slab_section={slab_section}"
                )
                return None

            return self.create_slab(
                corner_points, slab_section, center_point, slab_name, slab_tag, stb_guid
            )

        except Exception as e:
            self.logger.error(f"スラブ作成エラー: {e}")
            return None

    @staticmethod
    def create_slab_from_definition(definition: dict, index: int) -> Any:
        """定義辞書からスラブを作成"""
        creator = SlabCreator()
        return creator.create_element(definition)

    def create_slab(
        self,
        corner_points: List[Point3D],
        slab_section: StructuralSection,
        center_point: Optional[Point3D] = None,
        slab_name: str = "Slab",
        slab_tag: str = "SL001",
        stb_guid: Optional[str] = None,
    ) -> Any:
        """スラブを作成

        Args:
            corner_points: 角点のリスト
            slab_section: スラブ断面
            center_point: 中心点（オプション）
            slab_name: スラブ名
            slab_tag: スラブタグ
            stb_guid: STB GUID

        Returns:
            作成されたIFCスラブ要素
        """
        if not self.project_builder or not self.project_builder.file:
            self.logger.warning(
                "プロジェクトビルダーまたはIFCファイルが設定されていません"
            )
            return None

        try:
            # 中心点を決定
            if center_point:
                effective_center = center_point
                self.logger.debug(f"スラブ '{slab_name}' の配置に提供された中心点を使用: ({center_point.x:.1f}, {center_point.y:.1f}, {center_point.z:.1f})")
            else:
                # center_pointが提供されていない場合は角点から計算
                effective_center = self._calculate_center_from_corners(corner_points)
                self.logger.debug(f"スラブ '{slab_name}' の配置に計算された中心点を使用: ({effective_center.x:.1f}, {effective_center.y:.1f}, {effective_center.z:.1f})")

            # スラブのジオメトリ作成（ローカル座標系）
            shape = self._create_slab_geometry(corner_points, slab_section, effective_center)

            if not shape:
                return None

            # 配置作成（中心点に配置）
            placement = self._create_placement(effective_center)

            # スラブオブジェクト作成
            slab = self._create_slab_object(
                placement, shape, slab_name, slab_tag, stb_guid
            )

            if slab:
                # プロパティ設定
                self._set_slab_properties(slab, corner_points, slab_section)
                self.logger.debug(f"スラブ '{slab_name}' を作成しました")

            return slab

        except Exception as e:
            self.logger.error(f"スラブ作成中にエラー: {e}")
            return None

    def _create_slab_geometry(
        self, corner_points: List[Point3D], slab_section: StructuralSection, center_point: Point3D = None
    ):
        """スラブジオメトリを作成（ローカル座標系）"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 中心点を計算（未提供の場合）
            if not center_point:
                center_point = self._calculate_center_from_corners(corner_points)

            # ローカル座標系でポリゴンを作成（中心点を原点とする）
            ifc_points = []
            for point in corner_points:
                # 中心点からの相対座標に変換
                local_x = float(point.x - center_point.x)
                local_y = float(point.y - center_point.y)
                local_z = float(point.z - center_point.z)
                
                ifc_points.append(
                    ifc_file.createIfcCartesianPoint([local_x, local_y, local_z])
                )

            # 最初の点を最後に追加してポリゴンを閉じる
            ifc_points.append(ifc_points[0])

            # ポリライン作成
            polyline = ifc_file.createIfcPolyline(ifc_points)

            # プロファイルを作成（IFC仕様に準拠）
            profile = ifc_file.createIfcArbitraryClosedProfileDef(
                ProfileType="AREA",
                ProfileName=None,
                OuterCurve=polyline
            )

            # スラブの厚さを取得
            thickness = slab_section.properties.get(
                "thickness", 150.0
            )  # デフォルト150mm

            # 押し出し方向（通常はZ軸の負方向）
            direction = ifc_file.createIfcDirection([0.0, 0.0, -1.0])

            # 押し出し実体を作成
            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile,
                Position=None,
                ExtrudedDirection=direction,
                Depth=thickness,
            )

            return solid

        except Exception as e:
            self.logger.error(f"スラブジオメトリ作成エラー: {e}")
            return None

    def _create_placement(self, reference_point: Point3D):
        """配置を作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 参照点を配置位置として使用
            location = ifc_file.createIfcCartesianPoint(
                [
                    float(reference_point.x),
                    float(reference_point.y),
                    float(reference_point.z),
                ]
            )

            # 簡易的な配置（回転なし）
            placement = ifc_file.createIfcAxis2Placement3D(
                Location=location,
                Axis=None,  # デフォルトZ軸
                RefDirection=None,  # デフォルトX軸
            )

            return ifc_file.createIfcLocalPlacement(
                PlacementRelTo=None, RelativePlacement=placement  # 絶対配置
            )

        except Exception as e:
            self.logger.error(f"配置作成エラー: {e}")
            return None

    def _create_slab_object(
        self, placement, shape, slab_name: str, slab_tag: str, stb_guid: Optional[str]
    ):
        """スラブオブジェクトを作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # GUIDを生成または変換
            from common.guid_utils import convert_stb_guid_to_ifc, create_ifc_guid

            try:
                if stb_guid:
                    element_guid = convert_stb_guid_to_ifc(stb_guid)
                else:
                    element_guid = create_ifc_guid()
            except Exception:
                element_guid = create_ifc_guid()

            # 形状表現を作成
            if shape:
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=self.project_builder.model_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="SweptSolid",
                    Items=[shape],
                )

                product_shape = ifc_file.createIfcProductDefinitionShape(
                    Representations=[shape_representation]
                )
            else:
                product_shape = None

            # IFCスラブオブジェクトを作成
            slab = ifc_file.createIfcSlab(
                GlobalId=element_guid,
                OwnerHistory=self.project_builder.owner_history,
                Name=slab_name,
                Description=None,
                ObjectType=None,
                ObjectPlacement=placement,
                Representation=product_shape,
                Tag=slab_tag,
                PredefinedType="FLOOR",  # スラブタイプをFLOORに設定
            )

            return slab

        except Exception as e:
            self.logger.error(f"スラブオブジェクト作成エラー: {e}")
            return None

    def _set_slab_properties(
        self, slab, corner_points: List[Point3D], slab_section: StructuralSection
    ):
        """スラブプロパティを設定"""
        # 簡易実装 - 実際の実装では材料・断面プロパティを設定
        pass

    def _calculate_center_from_corners(self, corner_points: List[Point3D]) -> Point3D:
        """角点から中心点を計算"""
        if not corner_points:
            raise ValueError("角点リストが空です")
        
        center_x = sum(point.x for point in corner_points) / len(corner_points)
        center_y = sum(point.y for point in corner_points) / len(corner_points) 
        center_z = sum(point.z for point in corner_points) / len(corner_points)
        
        return Point3D(center_x, center_y, center_z)

    def create_slabs(self, slab_definitions: list) -> list:
        """複数のスラブを作成"""
        return self.create_elements(slab_definitions)
