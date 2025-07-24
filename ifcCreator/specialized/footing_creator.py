"""IFC Footing 作成クラス"""

import ifcopenshell
import logging
from typing import Dict, Any, Optional, List
from common.geometry import Point3D
from ..creators.base_creator import FoundationElementCreator
from ..utils.structural_section import StructuralSection as FootingSection


class IFCFootingCreator(FoundationElementCreator):
    """フーチング要素を作成するクラス"""

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """フーチング要素を作成（BaseElementCreatorの抽象メソッド実装）"""
        # 簡易実装 - 実際のフーチング作成はcreate_footingで行う
        return None

    def __init__(self, project_builder=None):
        # v2.2.0: Simplified initialization
        super().__init__(project_builder)
        self.logger = logging.getLogger(__name__)

    def create_project_structure(
        self, project_name: str = "Footing Project"
    ) -> "ifcopenshell.file":
        return super().create_project_structure(project_name)

    def create_footing(
        self,
        bottom_point: Point3D,
        top_point: Point3D,
        section: FootingSection,
        footing_name: str = "Footing",
        footing_tag: str = "FT001",
        stb_guid: str | None = None,
    ):
        """簡易フーチング作成（v2.2.0対応）"""
        try:
            if not self.project_builder or not self.project_builder.file:
                self.logger.error("プロジェクトビルダーが設定されていません")
                return None

            # 簡易実装：基本的なIFCFooting要素を作成
            ifc_file = self.project_builder.file

            # 位置を作成
            location = ifc_file.createIfcCartesianPoint(
                [float(bottom_point.x), float(bottom_point.y), float(bottom_point.z)]
            )
            placement_3d = ifc_file.createIfcAxis2Placement3D(Location=location)
            placement = ifc_file.createIfcLocalPlacement(RelativePlacement=placement_3d)

            # GUIDを生成または変換
            from common.guid_utils import convert_stb_guid_to_ifc, create_ifc_guid

            try:
                if stb_guid:
                    element_guid = convert_stb_guid_to_ifc(stb_guid)
                else:
                    element_guid = create_ifc_guid()
            except Exception:
                element_guid = create_ifc_guid()

            # フーチングの3D形状を作成
            footing_shape = self._create_footing_geometry(
                bottom_point, top_point, section, ifc_file
            )
            
            # IFCFooting要素を作成（3D形状付き）
            footing = ifc_file.createIfcFooting(
                GlobalId=element_guid,
                OwnerHistory=self.project_builder.owner_history,
                Name=footing_name,
                ObjectPlacement=placement,
                Representation=footing_shape,
                Tag=footing_tag,
                PredefinedType="FOOTING_BEAM",
            )

            # フーチング作成完了をデバッグログに記録
            self.logger.debug(f"フーチングを作成しました: 名前={footing_name}, GUID={element_guid}")
            self.logger.debug(f"フーチング '{footing_name}' を作成しました")
            return footing

        except Exception as e:
            self.logger.error(f"フーチング作成エラー: {e}")
            return None

    def _create_footing_geometry(
        self, 
        bottom_point: Point3D, 
        top_point: Point3D, 
        section: FootingSection, 
        ifc_file
    ):
        """フーチングの3D形状を作成"""
        try:
            # sectionが辞書の場合とStructuralSectionオブジェクトの場合を両方サポートするヘルパー関数
            def get_section_property(key: str, default=None):
                if hasattr(section, 'properties'):
                    return section.properties.get(key, default)
                else:
                    return section.get(key, default)

            # デフォルト寸法（section情報から取得、なければデフォルト値）
            # STB抽出キー(width_x, width_y)に対応
            width = get_section_property('width_x', get_section_property('width_X', 1000.0))
            length = get_section_property('width_y', get_section_property('width_Y', 1000.0))
            height = get_section_property('depth', 600.0)

            # 矩形断面プロファイルを作成
            profile_def = ifc_file.createIfcRectangleProfileDef(
                ProfileType="AREA",
                ProfileName=f"FootingProfile_{width}x{length}",
                XDim=float(width),
                YDim=float(length)
            )

            # 押出方向（垂直上向き）
            extrusion_direction = ifc_file.createIfcDirection([0.0, 0.0, 1.0])
            
            # 押出しソリッドを作成
            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile_def,
                Position=None,
                ExtrudedDirection=extrusion_direction,
                Depth=float(height)
            )

            # 形状表現を作成
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=self.project_builder.get_3d_context(),
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=[solid]
            )

            # 製品定義形状を作成
            product_shape = ifc_file.createIfcProductDefinitionShape(
                Representations=[shape_representation]
            )

            return product_shape

        except Exception as e:
            self.logger.error(f"フーチング形状作成エラー: {e}")
            return None

    def create_footings(self, footing_defs: List[Dict]) -> List:
        """フーチング要素リストを作成"""
        footings = []
        for footing_def in footing_defs:
            try:
                footing = self.create_footing_from_definition(footing_def)
                if footing:
                    footings.append(footing)
            except Exception as e:
                self.logger.error(
                    f"フーチング作成エラー (ID: {footing_def.get('id', 'Unknown')}): {e}"
                )

        self.logger.info(f"フーチング作成完了: {len(footings)}個")
        return footings

    def create_footing_from_definition(self, footing_def: Dict) -> Optional[Any]:
        """フーチング定義からフーチング要素を作成"""
        try:
            # 座標情報の取得
            bottom_point = Point3D(
                footing_def.get("bottom_point", {}).get("x", 0.0),
                footing_def.get("bottom_point", {}).get("y", 0.0),
                footing_def.get("bottom_point", {}).get("z", 0.0),
            )

            # 厚さから上端点を計算
            thickness = footing_def.get("thickness", 1000.0)  # デフォルト1000mm
            top_point = Point3D(
                bottom_point.x, bottom_point.y, bottom_point.z + thickness
            )

            # 断面情報の取得
            section_info = footing_def.get("section_info", {})
            section = FootingSection(
                section_name=section_info.get("stb_name", "F1"),
                width_x=section_info.get("width_x", 1000.0),
                width_y=section_info.get("width_y", 1000.0),
                depth=section_info.get("depth", thickness),
                section_type=section_info.get("section_type", "RECTANGLE"),
            )

            # フーチング作成
            footing_name = footing_def.get("name", "Footing")
            footing_tag = footing_def.get("tag", f"FT_{footing_def.get('id', '001')}")
            stb_guid = footing_def.get("stb_guid")

            return self.create_footing(
                bottom_point=bottom_point,
                top_point=top_point,
                section=section,
                footing_name=footing_name,
                footing_tag=footing_tag,
                stb_guid=stb_guid,
            )

        except Exception as e:
            self.logger.error(f"フーチング定義解析エラー: {e}")
            return None
