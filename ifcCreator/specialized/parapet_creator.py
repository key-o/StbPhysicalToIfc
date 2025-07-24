"""Parapet Creator

Phase 2 基礎要素実装: パラペット（Parapet）専用クリエーター
屋上などの手すり壁要素を適切にIFC形式で表現
"""

import ifcopenshell
import logging
from typing import Dict, Any, Optional, List
from common.geometry import Point3D
from ..creators.base_creator import PlanarElementCreator
from ..utils.structural_section import StructuralSection
from ..utils.validator import Validator
from exceptions.custom_errors import ParameterValidationError, GeometryValidationError

logger = logging.getLogger(__name__)


class ParapetCreator(PlanarElementCreator):
    """パラペット作成クラス
    
    Phase 2: 屋上パラペット・手すり壁の専用実装
    - 低い壁状の形状
    - 適切な材料プロパティ設定
    - IFC標準準拠の表現（IfcWallとして作成、PARAPET typeで識別）
    """

    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "parapet"
        self.validator = Validator()
        self.logger = logger

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """パラペット要素を作成

        Args:
            definition: パラペット定義辞書
                - corner_nodes: コーナーノードリスト (List[Point3D/dict])
                - section: 断面情報
                - height: パラペット高さ (mm, デフォルト: 1200)
                - thickness: 厚さ (mm)
                - name: パラペット名
                - tag: タグ

        Returns:
            作成されたIFCパラペット要素（壁として実装）
        """
        try:
            # パラメータ検証
            self._validate_parapet_definition(definition)
            
            # 基本パラメータの抽出
            corner_nodes = [self._extract_point(node) for node in definition.get("corner_nodes", [])]
            section = definition.get("section", {})
            
            # 寸法情報の抽出
            height = definition.get("height", 1200.0)  # パラペットは通常低い
            thickness = definition.get("thickness", 
                                     section.get("thickness", 150.0) if isinstance(section, dict) else 150.0)
            
            # メタデータ
            parapet_name = definition.get("name", "パラペット")
            parapet_tag = definition.get("tag", "PP001")
            stb_guid = definition.get("stb_guid")

            # IFC要素作成
            return self._create_parapet_ifc(
                corner_nodes=corner_nodes,
                height=height,
                thickness=thickness,
                parapet_name=parapet_name,
                parapet_tag=parapet_tag,
                section=section,
                stb_guid=stb_guid
            )

        except Exception as e:
            self.logger.error(f"パラペット作成エラー: {e}")
            return None

    def _validate_parapet_definition(self, definition: Dict[str, Any]) -> None:
        """パラペット定義の検証"""
        if not isinstance(definition, dict):
            raise ParameterValidationError("パラペット", "definition", "定義は辞書である必要があります")

        # 必須フィールドのチェック
        required_fields = ["corner_nodes"]
        missing_fields = [field for field in required_fields if field not in definition]
        if missing_fields:
            raise ParameterValidationError(
                "パラペット", 
                "必須フィールド", 
                f"必須フィールドが不足しています: {', '.join(missing_fields)}"
            )

        # コーナーノードの検証
        corner_nodes = definition.get("corner_nodes", [])
        if not isinstance(corner_nodes, list) or len(corner_nodes) < 2:
            raise GeometryValidationError("パラペット", "corner_nodes", "最低2つのコーナーノードが必要です")

        # 各コーナーノードの検証
        for i, node in enumerate(corner_nodes):
            if not self._is_valid_point(node):
                raise GeometryValidationError("パラペット", f"corner_node_{i}", f"コーナーノード{i+1}が無効です")

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

    def _create_parapet_ifc(
        self, 
        corner_nodes: List[Point3D],
        height: float,
        thickness: float,
        parapet_name: str,
        parapet_tag: str,
        section: Any,
        stb_guid: Optional[str] = None
    ) -> Optional[Any]:
        """実際のIFCパラペット要素を作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                self.logger.error("プロジェクトビルダーが設定されていません")
                return None

            ifc_file = self.project_builder.file

            # 1. パラペットの基準点を計算（最初のコーナーノード）
            base_point = corner_nodes[0]

            # 2. 位置情報を作成
            location = ifc_file.createIfcCartesianPoint([
                float(base_point.x), 
                float(base_point.y), 
                float(base_point.z)
            ])

            # 3. 配置情報を作成
            placement = ifc_file.createIfcAxis2Placement3D(location)

            # 4. パラペットの形状を作成
            # 線形パラペットの場合（2点間）
            if len(corner_nodes) == 2:
                parapet_shape = self._create_linear_parapet_shape(
                    corner_nodes[0], corner_nodes[1], height, thickness
                )
            else:
                # 複数点のパラペット（L字型など）
                parapet_shape = self._create_polyline_parapet_shape(
                    corner_nodes, height, thickness
                )

            if not parapet_shape:
                self.logger.error("パラペット形状の作成に失敗しました")
                return None

            # 5. 形状表現を作成
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=self.project_builder.get_3d_context(),
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=[parapet_shape]
            )

            product_shape = ifc_file.createIfcProductDefinitionShape(
                Representations=[shape_representation]
            )

            # 6. IFCWall要素をパラペットタイプで作成
            parapet = ifc_file.createIfcWall(
                GlobalId=self.project_builder.create_guid(stb_guid),
                Name=parapet_name,
                Tag=parapet_tag,
                ObjectPlacement=ifc_file.createIfcLocalPlacement(
                    RelativePlacement=placement
                ),
                Representation=product_shape,
                PredefinedType="PARAPET"
            )

            # 7. 材料・プロパティの設定
            self._assign_parapet_properties(parapet, section, height, thickness, corner_nodes)

            # 8. 関連付け
            self.project_builder.relate_to_building_element(parapet)

            # パラペット長さを計算
            parapet_length = self._calculate_parapet_length(corner_nodes)
            
            self.logger.info(f"パラペット '{parapet_name}' を作成しました（長さ:{parapet_length:.1f}mm, 高さ:{height:.1f}mm, 厚さ:{thickness:.1f}mm）")
            return parapet

        except Exception as e:
            self.logger.error(f"IFCパラペット作成エラー: {e}")
            return None

    def _create_linear_parapet_shape(
        self, 
        start_point: Point3D, 
        end_point: Point3D, 
        height: float, 
        thickness: float
    ) -> Optional[Any]:
        """線形パラペットの形状を作成"""
        try:
            ifc_file = self.project_builder.file
            
            # パラペットの長さを計算
            import math
            length = math.sqrt(
                (end_point.x - start_point.x) ** 2 +
                (end_point.y - start_point.y) ** 2 +
                (end_point.z - start_point.z) ** 2
            )

            # 断面プロファイル（矩形）
            profile_def = ifc_file.createIfcRectangleProfileDef(
                ProfileType="AREA",
                ProfileName=f"ParapetProfile_{thickness}x{height}",
                XDim=float(thickness),
                YDim=float(height)
            )

            # 押し出し方向と距離
            if length > 0:
                direction = [
                    (end_point.x - start_point.x) / length,
                    (end_point.y - start_point.y) / length,
                    (end_point.z - start_point.z) / length
                ]
            else:
                direction = [1.0, 0.0, 0.0]

            extrusion_direction = ifc_file.createIfcDirection(direction)
            
            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile_def,
                Position=None,
                ExtrudedDirection=extrusion_direction,
                Depth=float(length)
            )

            return solid

        except Exception as e:
            self.logger.error(f"線形パラペット形状作成エラー: {e}")
            return None

    def _create_polyline_parapet_shape(
        self, 
        corner_nodes: List[Point3D], 
        height: float, 
        thickness: float
    ) -> Optional[Any]:
        """複数点パラペットの形状を作成"""
        try:
            ifc_file = self.project_builder.file

            # 簡略化：最初の2点間で線形パラペットを作成
            # 実際の実装では、全ての点を使用してより複雑な形状を作成する
            if len(corner_nodes) >= 2:
                return self._create_linear_parapet_shape(
                    corner_nodes[0], corner_nodes[1], height, thickness
                )
            
            return None

        except Exception as e:
            self.logger.error(f"複数点パラペット形状作成エラー: {e}")
            return None

    def _calculate_parapet_length(self, corner_nodes: List[Point3D]) -> float:
        """パラペット全体の長さを計算"""
        total_length = 0.0
        import math
        
        for i in range(len(corner_nodes) - 1):
            start = corner_nodes[i]
            end = corner_nodes[i + 1]
            
            length = math.sqrt(
                (end.x - start.x) ** 2 +
                (end.y - start.y) ** 2 +
                (end.z - start.z) ** 2
            )
            total_length += length
            
        return total_length

    def _assign_parapet_properties(
        self, 
        parapet: Any, 
        section: Any, 
        height: float,
        thickness: float,
        corner_nodes: List[Point3D]
    ) -> None:
        """パラペットにプロパティを割り当て"""
        try:
            if not self.project_builder:
                return

            # 寸法プロパティセット
            parapet_length = self._calculate_parapet_length(corner_nodes)
            dimension_props = {
                "Height": height,
                "Thickness": thickness,
                "Length": parapet_length,
                "CrossSectionalArea": thickness * height,
                "Volume": thickness * height * parapet_length
            }

            # 材料情報
            material_props = {}
            if isinstance(section, dict):
                material_props.update({
                    "MaterialType": section.get("material_type", "コンクリート"),
                    "ConcreteStrength": section.get("strength_concrete", "Fc21"),
                    "SectionType": section.get("section_type", "RECT"),
                    "ElementType": "PARAPET"
                })

            # プロパティセットを作成・関連付け
            self.project_builder.create_property_set(
                parapet,
                "Pset_ParapetDimensions", 
                dimension_props
            )

            if material_props:
                self.project_builder.create_property_set(
                    parapet,
                    "Pset_ParapetMaterial",
                    material_props
                )

        except Exception as e:
            self.logger.warning(f"パラペットプロパティ設定エラー: {e}")