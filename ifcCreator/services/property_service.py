"""Property Service

統一プロパティ管理サービス
v2.2.0: 簡素化された統一実装
"""

from typing import List, Optional, Dict, Any, Union
import logging
from common.guid_utils import create_ifc_guid

# v2.2.0: 統合アーキテクチャ - 簡素化されたプロパティ管理

logger = logging.getLogger(__name__)


class PropertyService:
    """プロパティ管理の統一サービス

    v2.2.0: 簡素化された統一実装
    """

    def __init__(self, ifc_file=None):
        """PropertyServiceの初期化

        Args:
            ifc_file: IFCファイルオブジェクト（オプション）
        """
        self.file = ifc_file

    def create_element_properties(
        self,
        element_type: str,
        definition: Dict[str, Any],
        element_instance,
        profile=None,
    ) -> List:
        """要素タイプ別プロパティ作成

        Args:
            element_type: 要素タイプ (beam, column, slab, wall, etc.)
            definition: 要素定義辞書
            element_instance: IFC要素インスタンス
            profile: プロファイル（線要素の場合）

        Returns:
            作成されたプロパティのリスト
        """
        # v2.2.0: 簡素化されたプロパティ作成
        try:
            logger.debug(f"Creating properties for {element_type}")
            return self._create_simple_properties(
                element_type, definition, element_instance
            )

        except Exception as e:
            logger.error(f"Failed to create properties for {element_type}: {e}")
            return []

    def _create_simple_properties(
        self, element_type: str, definition: Dict[str, Any], element_instance
    ) -> List:
        """IFCプロパティセット作成

        v2.2.0: 拡張実装 - 旧版と同等のプロパティセット作成
        """
        if not self.file:
            logger.warning("IFCファイルが設定されていません")
            return []

        properties = []

        try:
            if element_type.lower() == "beam":
                properties.extend(
                    self._create_beam_properties(definition, element_instance)
                )
            elif element_type.lower() == "column":
                properties.extend(
                    self._create_column_properties(definition, element_instance)
                )
            elif element_type.lower() == "slab":
                properties.extend(
                    self._create_slab_properties(definition, element_instance)
                )
            elif element_type.lower() == "wall":
                properties.extend(
                    self._create_wall_properties(definition, element_instance)
                )
            elif element_type.lower() == "brace":
                properties.extend(
                    self._create_brace_properties(definition, element_instance)
                )

        except Exception as e:
            logger.error(f"要素プロパティの設定に失敗しました。詳細: {e}")

        return properties

    def _create_beam_properties(
        self, definition: Dict[str, Any], element_instance
    ) -> List:
        """梁用プロパティセット作成"""
        properties = []

        # Pset_BeamCommon
        beam_common_props = [
            self.file.createIfcPropertySingleValue(
                "Reference",
                None,
                self.file.createIfcLabel(definition.get("tag", "")),
                None,
            ),
            self.file.createIfcPropertySingleValue(
                "IsExternal", None, self.file.createIfcBoolean(False), None
            ),
            self.file.createIfcPropertySingleValue(
                "LoadBearing", None, self.file.createIfcBoolean(True), None
            ),
            self.file.createIfcPropertySingleValue(
                "FireRating", None, self.file.createIfcLabel(""), None
            ),
        ]

        pset_beam_common = self.file.createIfcPropertySet(
            GlobalId=create_ifc_guid(),
            Name="Pset_BeamCommon",
            HasProperties=beam_common_props,
        )

        rel_beam_common = self.file.createIfcRelDefinesByProperties(
            GlobalId=create_ifc_guid(),
            RelatedObjects=[element_instance],
            RelatingPropertyDefinition=pset_beam_common,
        )

        properties.extend([pset_beam_common, rel_beam_common])

        # Pset_BeamReferenceLineCoordinates (座標プロパティ)
        if "start_point" in definition and "end_point" in definition:
            start_point = definition["start_point"]
            end_point = definition["end_point"]

            coord_props = [
                self.file.createIfcPropertySingleValue(
                    "StartPointX",
                    None,
                    self.file.createIfcLengthMeasure(start_point.x),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "StartPointY",
                    None,
                    self.file.createIfcLengthMeasure(start_point.y),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "StartPointZ",
                    None,
                    self.file.createIfcLengthMeasure(start_point.z),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "EndPointX",
                    None,
                    self.file.createIfcLengthMeasure(end_point.x),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "EndPointY",
                    None,
                    self.file.createIfcLengthMeasure(end_point.y),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "EndPointZ",
                    None,
                    self.file.createIfcLengthMeasure(end_point.z),
                    None,
                ),
            ]

            pset_coord = self.file.createIfcPropertySet(
                GlobalId=create_ifc_guid(),
                Name="Pset_BeamReferenceLineCoordinates",
                HasProperties=coord_props,
            )

            rel_coord = self.file.createIfcRelDefinesByProperties(
                GlobalId=create_ifc_guid(),
                RelatedObjects=[element_instance],
                RelatingPropertyDefinition=pset_coord,
            )

            properties.extend([pset_coord, rel_coord])

        # Pset_SectionDimensions (断面寸法プロパティ)
        if "section" in definition:
            section = definition["section"]
            section_props = []

            if hasattr(section, "width") and section.width:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "Width",
                        None,
                        self.file.createIfcLengthMeasure(section.width),
                        None,
                    )
                )
            if hasattr(section, "height") and section.height:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "Height",
                        None,
                        self.file.createIfcLengthMeasure(section.height),
                        None,
                    )
                )
            if hasattr(section, "thickness") and section.thickness:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "Thickness",
                        None,
                        self.file.createIfcLengthMeasure(section.thickness),
                        None,
                    )
                )

            if section_props:
                pset_section = self.file.createIfcPropertySet(
                    GlobalId=create_ifc_guid(),
                    Name="Pset_SectionDimensions",
                    HasProperties=section_props,
                )

                rel_section = self.file.createIfcRelDefinesByProperties(
                    GlobalId=create_ifc_guid(),
                    RelatedObjects=[element_instance],
                    RelatingPropertyDefinition=pset_section,
                )

                properties.extend([pset_section, rel_section])

        return properties

    def _create_column_properties(
        self, definition: Dict[str, Any], element_instance
    ) -> List:
        """柱用プロパティセット作成"""
        properties = []

        # Pset_ColumnCommon
        column_common_props = [
            self.file.createIfcPropertySingleValue(
                "Reference",
                None,
                self.file.createIfcLabel(definition.get("tag", "")),
                None,
            ),
            self.file.createIfcPropertySingleValue(
                "IsExternal", None, self.file.createIfcBoolean(False), None
            ),
            self.file.createIfcPropertySingleValue(
                "LoadBearing", None, self.file.createIfcBoolean(True), None
            ),
            self.file.createIfcPropertySingleValue(
                "FireRating", None, self.file.createIfcLabel(""), None
            ),
        ]

        pset_column_common = self.file.createIfcPropertySet(
            GlobalId=create_ifc_guid(),
            Name="Pset_ColumnCommon",
            HasProperties=column_common_props,
        )

        rel_column_common = self.file.createIfcRelDefinesByProperties(
            GlobalId=create_ifc_guid(),
            RelatedObjects=[element_instance],
            RelatingPropertyDefinition=pset_column_common,
        )

        properties.extend([pset_column_common, rel_column_common])

        # Pset_ColumnCoordinates
        if "start_point" in definition and "end_point" in definition:
            start_point = definition["start_point"]
            end_point = definition["end_point"]
            height = abs(end_point.z - start_point.z)

            coord_props = [
                self.file.createIfcPropertySingleValue(
                    "BottomPointX",
                    None,
                    self.file.createIfcLengthMeasure(start_point.x),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "BottomPointY",
                    None,
                    self.file.createIfcLengthMeasure(start_point.y),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "BottomPointZ",
                    None,
                    self.file.createIfcLengthMeasure(start_point.z),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "TopPointX",
                    None,
                    self.file.createIfcLengthMeasure(end_point.x),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "TopPointY",
                    None,
                    self.file.createIfcLengthMeasure(end_point.y),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "TopPointZ",
                    None,
                    self.file.createIfcLengthMeasure(end_point.z),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "Height", None, self.file.createIfcLengthMeasure(height), None
                ),
            ]

            pset_coord = self.file.createIfcPropertySet(
                GlobalId=create_ifc_guid(),
                Name="Pset_ColumnCoordinates",
                HasProperties=coord_props,
            )

            rel_coord = self.file.createIfcRelDefinesByProperties(
                GlobalId=create_ifc_guid(),
                RelatedObjects=[element_instance],
                RelatingPropertyDefinition=pset_coord,
            )

            properties.extend([pset_coord, rel_coord])

        # Pset_ColumnSectionDimensions
        if "section" in definition:
            section = definition["section"]
            section_props = []

            if hasattr(section, "width") and section.width:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "Width",
                        None,
                        self.file.createIfcLengthMeasure(section.width),
                        None,
                    )
                )
            if hasattr(section, "height") and section.height:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "Height",
                        None,
                        self.file.createIfcLengthMeasure(section.height),
                        None,
                    )
                )
            if hasattr(section, "thickness") and section.thickness:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "WallThickness",
                        None,
                        self.file.createIfcLengthMeasure(section.thickness),
                        None,
                    )
                )

            if section_props:
                pset_section = self.file.createIfcPropertySet(
                    GlobalId=create_ifc_guid(),
                    Name="Pset_ColumnSectionDimensions",
                    HasProperties=section_props,
                )

                rel_section = self.file.createIfcRelDefinesByProperties(
                    GlobalId=create_ifc_guid(),
                    RelatedObjects=[element_instance],
                    RelatingPropertyDefinition=pset_section,
                )

                properties.extend([pset_section, rel_section])

        return properties

    def _create_slab_properties(
        self, definition: Dict[str, Any], element_instance
    ) -> List:
        """スラブ用プロパティセット作成"""
        properties = []

        # Pset_SlabCommon
        slab_common_props = [
            self.file.createIfcPropertySingleValue(
                "Reference",
                None,
                self.file.createIfcLabel(definition.get("tag", "")),
                None,
            ),
            self.file.createIfcPropertySingleValue(
                "IsExternal", None, self.file.createIfcBoolean(False), None
            ),
            self.file.createIfcPropertySingleValue(
                "LoadBearing", None, self.file.createIfcBoolean(True), None
            ),
            self.file.createIfcPropertySingleValue(
                "FireRating", None, self.file.createIfcLabel(""), None
            ),
        ]

        pset_slab_common = self.file.createIfcPropertySet(
            GlobalId=create_ifc_guid(),
            Name="Pset_SlabCommon",
            HasProperties=slab_common_props,
        )

        rel_slab_common = self.file.createIfcRelDefinesByProperties(
            GlobalId=create_ifc_guid(),
            RelatedObjects=[element_instance],
            RelatingPropertyDefinition=pset_slab_common,
        )

        properties.extend([pset_slab_common, rel_slab_common])

        return properties

    def _create_wall_properties(
        self, definition: Dict[str, Any], element_instance
    ) -> List:
        """壁用プロパティセット作成"""
        properties = []

        # Pset_WallCommon
        wall_common_props = [
            self.file.createIfcPropertySingleValue(
                "Reference",
                None,
                self.file.createIfcLabel(definition.get("tag", "")),
                None,
            ),
            self.file.createIfcPropertySingleValue(
                "IsExternal", None, self.file.createIfcBoolean(False), None
            ),
            self.file.createIfcPropertySingleValue(
                "LoadBearing", None, self.file.createIfcBoolean(True), None
            ),
            self.file.createIfcPropertySingleValue(
                "FireRating", None, self.file.createIfcLabel(""), None
            ),
        ]

        pset_wall_common = self.file.createIfcPropertySet(
            GlobalId=create_ifc_guid(),
            Name="Pset_WallCommon",
            HasProperties=wall_common_props,
        )

        rel_wall_common = self.file.createIfcRelDefinesByProperties(
            GlobalId=create_ifc_guid(),
            RelatedObjects=[element_instance],
            RelatingPropertyDefinition=pset_wall_common,
        )

        properties.extend([pset_wall_common, rel_wall_common])

        return properties

    def _create_brace_properties(
        self, definition: Dict[str, Any], element_instance
    ) -> List:
        """ブレース用プロパティセット作成
        
        Phase2強化: ブレース専用プロパティセット
        """
        properties = []

        # Pset_MemberCommon (ブレースはIfcMemberとして作成されるため)
        brace_common_props = [
            self.file.createIfcPropertySingleValue(
                "Reference",
                None,
                self.file.createIfcLabel(definition.get("tag", "")),
                None,
            ),
            self.file.createIfcPropertySingleValue(
                "IsExternal", None, self.file.createIfcBoolean(False), None
            ),
            self.file.createIfcPropertySingleValue(
                "LoadBearing", None, self.file.createIfcBoolean(True), None
            ),
            self.file.createIfcPropertySingleValue(
                "FireRating", None, self.file.createIfcLabel(""), None
            ),
        ]

        pset_brace_common = self.file.createIfcPropertySet(
            GlobalId=create_ifc_guid(),
            Name="Pset_MemberCommon",
            HasProperties=brace_common_props,
        )

        rel_brace_common = self.file.createIfcRelDefinesByProperties(
            GlobalId=create_ifc_guid(),
            RelatedObjects=[element_instance],
            RelatingPropertyDefinition=pset_brace_common,
        )

        properties.extend([pset_brace_common, rel_brace_common])

        # Pset_BraceCoordinates (ブレース専用座標プロパティ)
        if "start_point" in definition and "end_point" in definition:
            start_point = definition["start_point"]
            end_point = definition["end_point"]

            coord_props = [
                self.file.createIfcPropertySingleValue(
                    "StartPointX",
                    None,
                    self.file.createIfcLengthMeasure(start_point.x),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "StartPointY",
                    None,
                    self.file.createIfcLengthMeasure(start_point.y),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "StartPointZ",
                    None,
                    self.file.createIfcLengthMeasure(start_point.z),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "EndPointX",
                    None,
                    self.file.createIfcLengthMeasure(end_point.x),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "EndPointY",
                    None,
                    self.file.createIfcLengthMeasure(end_point.y),
                    None,
                ),
                self.file.createIfcPropertySingleValue(
                    "EndPointZ",
                    None,
                    self.file.createIfcLengthMeasure(end_point.z),
                    None,
                ),
            ]

            # ブレース長さを計算
            import math
            length = math.sqrt(
                (end_point.x - start_point.x) ** 2
                + (end_point.y - start_point.y) ** 2
                + (end_point.z - start_point.z) ** 2
            )
            coord_props.append(
                self.file.createIfcPropertySingleValue(
                    "Length",
                    None,
                    self.file.createIfcLengthMeasure(length),
                    None,
                )
            )

            pset_coord = self.file.createIfcPropertySet(
                GlobalId=create_ifc_guid(),
                Name="Pset_BraceCoordinates",
                HasProperties=coord_props,
            )

            rel_coord = self.file.createIfcRelDefinesByProperties(
                GlobalId=create_ifc_guid(),
                RelatedObjects=[element_instance],
                RelatingPropertyDefinition=pset_coord,
            )

            properties.extend([pset_coord, rel_coord])

        # Pset_BraceSectionDimensions (ブレース断面寸法プロパティ)
        if "section" in definition:
            section = definition["section"]
            section_props = []

            # ブレース特有の断面情報
            if hasattr(section, "section_type"):
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "SectionType",
                        None,
                        self.file.createIfcLabel(section.section_type),
                        None,
                    )
                )

            # L形断面の場合
            if hasattr(section, "overall_depth") and section.overall_depth:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "OverallDepth",
                        None,
                        self.file.createIfcLengthMeasure(section.overall_depth),
                        None,
                    )
                )
            if hasattr(section, "flange_width") and section.flange_width:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "FlangeWidth",
                        None,
                        self.file.createIfcLengthMeasure(section.flange_width),
                        None,
                    )
                )
            if hasattr(section, "web_thickness") and section.web_thickness:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "WebThickness",
                        None,
                        self.file.createIfcLengthMeasure(section.web_thickness),
                        None,
                    )
                )
            if hasattr(section, "flange_thickness") and section.flange_thickness:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "FlangeThickness",
                        None,
                        self.file.createIfcLengthMeasure(section.flange_thickness),
                        None,
                    )
                )

            # 汎用寸法プロパティ
            if hasattr(section, "width") and section.width:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "Width",
                        None,
                        self.file.createIfcLengthMeasure(section.width),
                        None,
                    )
                )
            if hasattr(section, "height") and section.height:
                section_props.append(
                    self.file.createIfcPropertySingleValue(
                        "Height",
                        None,
                        self.file.createIfcLengthMeasure(section.height),
                        None,
                    )
                )

            if section_props:
                pset_section = self.file.createIfcPropertySet(
                    GlobalId=create_ifc_guid(),
                    Name="Pset_BraceSectionDimensions",
                    HasProperties=section_props,
                )

                rel_section = self.file.createIfcRelDefinesByProperties(
                    GlobalId=create_ifc_guid(),
                    RelatedObjects=[element_instance],
                    RelatingPropertyDefinition=pset_section,
                )

                properties.extend([pset_section, rel_section])

        return properties

    def create_material_properties(
        self, material_name: str, strength_class: str = None
    ) -> Dict[str, Any]:
        """材料プロパティを作成

        Args:
            material_name: 材料名
            strength_class: 強度クラス

        Returns:
            材料プロパティ辞書
        """
        return {
            "material_name": material_name,
            "strength_class": strength_class or "Default",
            "created_by": "PropertyService v2.2.0",
        }

    def create_structural_properties(
        self, section_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """構造プロパティを作成

        Args:
            section_data: 断面データ

        Returns:
            構造プロパティ辞書
        """
        return {
            "section_type": section_data.get("section_type", "Unknown"),
            "dimensions": section_data.get("dimensions", {}),
            "created_by": "PropertyService v2.2.0",
        }

    def get_property_manager(self, element_type: str):
        """要素タイプ別プロパティマネージャーを取得

        旧版PropertyManagerBaseの機能を統合
        """
        # 統一されたプロパティマネージャーとして自身を返す
        return self

    # === 旧版PropertyManagerBaseから移植したメソッド ===

    def create_structural_properties(self, property_data: Dict[str, tuple]) -> list:
        """構造要素の共通プロパティを一括作成

        Args:
            property_data: {property_name: (property_type, value)} の辞書
                property_type: "boolean", "label", "length", "identifier"

        Returns:
            作成されたプロパティのリスト
        """
        if not self.file:
            logger.warning("IFC file not available for property creation")
            return []

        properties = []

        for prop_name, (prop_type, value) in property_data.items():
            if value is None:
                continue

            try:
                if prop_type == "boolean":
                    properties.append(self._create_boolean_property(prop_name, value))
                elif prop_type == "label":
                    properties.append(
                        self._create_label_property(prop_name, str(value))
                    )
                elif prop_type == "length":
                    properties.append(
                        self._create_length_property(prop_name, float(value))
                    )
                elif prop_type == "identifier":
                    properties.append(
                        self._create_identifier_property(prop_name, str(value))
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"プロパティ '{prop_name}' の作成に失敗: {e}")
                continue

        return properties

    def _create_boolean_property(self, name: str, value: bool):
        """ブール値プロパティを作成"""
        return self.file.createIfcPropertySingleValue(
            Name=name, NominalValue=self.file.createIfcBoolean(value)
        )

    def _create_label_property(self, name: str, value: str):
        """ラベルプロパティを作成"""
        return self.file.createIfcPropertySingleValue(
            Name=name, NominalValue=self.file.createIfcLabel(value)
        )

    def _create_length_property(self, name: str, value: float):
        """長さプロパティを作成"""
        return self.file.createIfcPropertySingleValue(
            Name=name, NominalValue=self.file.createIfcLengthMeasure(value)
        )

    def _create_identifier_property(self, name: str, value: str):
        """識別子プロパティを作成"""
        return self.file.createIfcPropertySingleValue(
            Name=name, NominalValue=self.file.createIfcIdentifier(value)
        )

    def create_property_set(self, name: str, properties: list, target_object):
        """プロパティセットを作成して関連付け"""
        if not self.file:
            logger.warning("IFC file not available for property set creation")
            return None

        import uuid
        import ifcopenshell

        # GUID生成
        guid = ifcopenshell.guid.compress(uuid.uuid4().hex)

        pset = self.file.createIfcPropertySet(
            GlobalId=guid,
            OwnerHistory=None,  # owner_historyは要求に応じて設定
            Name=name,
            HasProperties=properties,
        )

        # 関連付け作成
        rel_guid = ifcopenshell.guid.compress(uuid.uuid4().hex)
        self.file.createIfcRelDefinesByProperties(
            GlobalId=rel_guid,
            OwnerHistory=None,
            RelatedObjects=[target_object],
            RelatingPropertyDefinition=pset,
        )

        return pset
