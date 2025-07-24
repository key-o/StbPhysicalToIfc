"""Strip Footing Creator

Phase 2 基礎要素実装: 連続基礎（Strip Footing）専用クリエーター
壁下の連続基礎を適切にIFC形式で表現
"""

import ifcopenshell
import logging
from typing import Dict, Any, Optional, List
from common.geometry import Point3D
from ..creators.base_creator import FoundationElementCreator
from ..utils.structural_section import StructuralSection
from ..utils.validator import Validator
from exceptions.custom_errors import ParameterValidationError, GeometryValidationError

logger = logging.getLogger(__name__)


class StripFootingCreator(FoundationElementCreator):
    """連続基礎作成クラス
    
    Phase 2: 壁下連続基礎の専用実装
    - 線形の連続基礎形状
    - 適切な材料プロパティ設定
    - IFC標準準拠の表現
    """

    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "strip_footing"
        self.validator = Validator()
        self.logger = logger

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """連続基礎要素を作成

        Args:
            definition: 連続基礎定義辞書
                - start_point: 開始点 (Point3D or dict)
                - end_point: 終了点 (Point3D or dict)
                - section: 断面情報
                - width: 基礎幅 (mm)
                - height: 基礎高さ (mm) 
                - depth: 根入れ深さ (mm)
                - name: 基礎名
                - tag: タグ

        Returns:
            作成されたIFC連続基礎要素
        """
        try:
            # パラメータ検証
            self._validate_strip_footing_definition(definition)
            
            # 基本パラメータの抽出
            start_point = self._extract_point(definition.get("start_point"))
            end_point = self._extract_point(definition.get("end_point"))
            section = definition.get("section")
            
            # 寸法情報の抽出
            width = definition.get("width", section.get("width", 1000.0) if isinstance(section, dict) else 1000.0)
            height = definition.get("height", section.get("height", 600.0) if isinstance(section, dict) else 600.0)
            depth = definition.get("depth", section.get("depth", 800.0) if isinstance(section, dict) else 800.0)
            
            # メタデータ
            footing_name = definition.get("name", "連続基礎")
            footing_tag = definition.get("tag", "SF001")
            stb_guid = definition.get("stb_guid")

            # IFC要素作成
            return self._create_strip_footing_ifc(
                start_point=start_point,
                end_point=end_point,
                width=width,
                height=height,
                depth=depth,
                footing_name=footing_name,
                footing_tag=footing_tag,
                section=section,
                stb_guid=stb_guid
            )

        except Exception as e:
            self.logger.error(f"連続基礎作成エラー: {e}")
            return None

    def _validate_strip_footing_definition(self, definition: Dict[str, Any]) -> None:
        """連続基礎定義の検証"""
        if not isinstance(definition, dict):
            raise ParameterValidationError("連続基礎", "definition", "定義は辞書である必要があります")

        # 必須フィールドのチェック
        required_fields = ["start_point", "end_point"]
        missing_fields = [field for field in required_fields if field not in definition]
        if missing_fields:
            raise ParameterValidationError(
                "連続基礎", 
                "必須フィールド", 
                f"必須フィールドが不足しています: {', '.join(missing_fields)}"
            )

        # 座標点の検証
        start_point = definition.get("start_point")
        end_point = definition.get("end_point")
        
        if not self._is_valid_point(start_point):
            raise GeometryValidationError("連続基礎", "start_point", "開始点が無効です")
        
        if not self._is_valid_point(end_point):
            raise GeometryValidationError("連続基礎", "end_point", "終了点が無効です")

        # 基礎の長さをチェック
        if self._points_are_identical(start_point, end_point):
            raise GeometryValidationError("連続基礎", "length", "開始点と終了点が同一です")

    def _extract_point(self, point_data: Any) -> Point3D:
        """座標データをPoint3Dに変換"""
        if isinstance(point_data, Point3D):
            return point_data
        elif isinstance(point_data, dict):
            return Point3D(
                point_data.get("x", 0.0),
                point_data.get("y", 0.0),
                point_data.get("z", 0.0)
            )
        else:
            raise ValueError(f"無効な座標データ: {point_data}")

    def _is_valid_point(self, point_data: Any) -> bool:
        """座標点の有効性をチェック"""
        if isinstance(point_data, Point3D):
            return True
        elif isinstance(point_data, dict):
            return all(coord in point_data for coord in ["x", "y", "z"])
        return False

    def _points_are_identical(self, point1: Any, point2: Any, tolerance: float = 1e-6) -> bool:
        """2つの点が同一かチェック"""
        p1 = self._extract_point(point1)
        p2 = self._extract_point(point2)
        
        return (abs(p1.x - p2.x) < tolerance and 
                abs(p1.y - p2.y) < tolerance and 
                abs(p1.z - p2.z) < tolerance)

    def _create_strip_footing_ifc(
        self, 
        start_point: Point3D, 
        end_point: Point3D,
        width: float,
        height: float, 
        depth: float,
        footing_name: str,
        footing_tag: str,
        section: Any,
        stb_guid: Optional[str] = None
    ) -> Optional[Any]:
        """実際のIFC連続基礎要素を作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                self.logger.error("プロジェクトビルダーが設定されていません")
                return None

            ifc_file = self.project_builder.file

            # 1. 基礎の中心点と方向を計算
            center_point = Point3D(
                (start_point.x + end_point.x) / 2,
                (start_point.y + end_point.y) / 2,
                (start_point.z + end_point.z) / 2 - depth / 2  # 根入れ深さを考慮
            )

            # 2. 基礎の長さを計算
            import math
            footing_length = math.sqrt(
                (end_point.x - start_point.x) ** 2 +
                (end_point.y - start_point.y) ** 2 +
                (start_point.z - end_point.z) ** 2
            )

            # 3. 位置情報を作成
            location = ifc_file.createIfcCartesianPoint([
                float(center_point.x), 
                float(center_point.y), 
                float(center_point.z)
            ])

            # 4. 方向を計算（X軸方向ベクトル）
            if footing_length > 0:
                direction_x = [(end_point.x - start_point.x) / footing_length,
                              (end_point.y - start_point.y) / footing_length, 0.0]
            else:
                direction_x = [1.0, 0.0, 0.0]

            direction_z = [0.0, 0.0, 1.0]
            
            axis_x = ifc_file.createIfcDirection(direction_x)
            axis_z = ifc_file.createIfcDirection(direction_z)

            # 5. 配置情報を作成
            placement = ifc_file.createIfcAxis2Placement3D(location, axis_z, axis_x)

            # 6. 形状を作成（直方体の押し出し）
            # 断面プロファイル（矩形）
            profile_def = ifc_file.createIfcRectangleProfileDef(
                ProfileType="AREA",
                ProfileName=f"{footing_name}_Profile",
                XDim=float(width),
                YDim=float(height)
            )

            # 押し出し方向と距離
            extrusion_direction = ifc_file.createIfcDirection([1.0, 0.0, 0.0])
            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile_def,
                Position=None,
                ExtrudedDirection=extrusion_direction,
                Depth=float(footing_length)
            )

            # 7. 形状表現を作成
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=self.project_builder.get_3d_context(),
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=[solid]
            )

            product_shape = ifc_file.createIfcProductDefinitionShape(
                Representations=[shape_representation]
            )

            # 8. IFCFooting要素を作成
            footing = ifc_file.createIfcFooting(
                GlobalId=self.project_builder.create_guid(stb_guid),
                Name=footing_name,
                Tag=footing_tag,
                ObjectPlacement=ifc_file.createIfcLocalPlacement(
                    RelativePlacement=placement
                ),
                Representation=product_shape,
                PredefinedType="STRIP_FOOTING"
            )

            # 9. 材料・プロパティの設定
            self._assign_footing_properties(footing, section, width, height, depth, footing_length)

            # 10. 関連付け
            self.project_builder.relate_to_building_element(footing)

            self.logger.info(f"連続基礎 '{footing_name}' を作成しました（長さ:{footing_length:.1f}mm, 幅:{width:.1f}mm, 高さ:{height:.1f}mm）")
            return footing

        except Exception as e:
            self.logger.error(f"IFC連続基礎作成エラー: {e}")
            return None

    def _assign_footing_properties(
        self, 
        footing: Any, 
        section: Any, 
        width: float, 
        height: float,
        depth: float,
        length: float
    ) -> None:
        """連続基礎にプロパティを割り当て"""
        try:
            if not self.project_builder:
                return

            # 寸法プロパティセット
            dimension_props = {
                "Width": width,
                "Height": height, 
                "Depth": depth,
                "Length": length,
                "CrossSectionalArea": width * height,
                "Volume": width * height * length
            }

            # 材料情報
            material_props = {}
            if isinstance(section, dict):
                material_props.update({
                    "MaterialType": section.get("material_type", "コンクリート"),
                    "ConcreteStrength": section.get("strength_concrete", "Fc21"),
                    "SectionType": section.get("section_type", "RECT")
                })

            # プロパティセットを作成・関連付け
            self.project_builder.create_property_set(
                footing,
                "Pset_StripFootingDimensions", 
                dimension_props
            )

            if material_props:
                self.project_builder.create_property_set(
                    footing,
                    "Pset_StripFootingMaterial",
                    material_props
                )

        except Exception as e:
            self.logger.warning(f"連続基礎プロパティ設定エラー: {e}")