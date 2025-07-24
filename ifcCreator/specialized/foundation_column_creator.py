# ifcCreator/foundation_column_creator.py
"""
IFC基礎柱作成のメインクラス（統合初期化対応）
"""
import ifcopenshell
import logging
from typing import Optional, Any
from common.geometry import Point3D
from ..creators.base_creator import StructuralElementCreatorBase
# v2.2.0: unified_initialization_factory not available in simplified structure
# from ..core.unified_initialization_factory import (
#     UnifiedInitializationFactory, InitializationMixin
# )
from ..utils.structural_section import StructuralSection as ColumnSection


logger = logging.getLogger(__name__)


class IFCFoundationColumnCreator(StructuralElementCreatorBase):
    """
    IFC基礎柱作成のメインクラス（統合初期化対応）
    StbFoundationColumn → IfcColumn として処理
    """
    
    def create_element(self, definition: dict) -> Optional[Any]:
        """基礎柱要素を作成（BaseElementCreatorの抽象メソッド実装）"""
        # 簡易実装 - 実際の基礎柱作成はcreate_foundation_columnで行う
        return None

    def __init__(self, project_builder=None):
        # v2.2.0: Simplified initialization
        super().__init__(project_builder)
        self.logger = logger

    def create_foundation_column(
        self, foundation_column_data: dict, building_storey, ifc_file: ifcopenshell.file
    ):
        """
        基礎柱の作成（IfcColumnとして実装）
        基礎柱は下の節点と上方向への長さで定義される

        Args:
            foundation_column_data: 基礎柱データ辞書
            building_storey: IfcBuildingStorey
            ifc_file: IFCファイル

        Returns:
            作成されたIfcColumn
        """
        try:
            logger.debug("基礎柱作成開始: %s", foundation_column_data.get("name", ""))

            # 基礎柱の位置情報（下の節点）
            x = foundation_column_data["x"]
            y = foundation_column_data["y"]
            z = foundation_column_data["z"]

            # WR部分の情報を取得（主要な立上り部分）
            wr_section = foundation_column_data.get("wr_section")
            if wr_section:
                # WR部分の寸法と長さを使用
                width = foundation_column_data["width"]  # WR部分から取得済み
                height = foundation_column_data["height"]  # WR部分から取得済み
                column_length = wr_section["length"]  # WR部分の長さ（上方向）
                logger.debug(
                    "WR部分を使用: 幅=%f, 高さ=%f, 長さ=%f",
                    width,
                    height,
                    column_length,
                )
            else:
                # FD部分のみの場合
                fd_section = foundation_column_data["fd_section"]
                width = foundation_column_data["width"]
                height = foundation_column_data["height"]
                column_length = foundation_column_data["depth"]  # FD部分の長さ
                logger.debug(
                    "FD部分を使用: 幅=%f, 高さ=%f, 長さ=%f",
                    width,
                    height,
                    column_length,
                )

            # 基礎柱の底面と頂面の点を計算（下の節点から上方向へ）
            bottom_point = Point3D(x, y, z)
            top_point = Point3D(x, y, z + column_length)  # 上方向への長さ

            logger.debug(
                "基礎柱位置: 底面=(%f, %f, %f), 頂面=(%f, %f, %f)",
                bottom_point.x,
                bottom_point.y,
                bottom_point.z,
                top_point.x,
                top_point.y,
                top_point.z,
            )  # 統一的なファクトリーメソッドを使用してColumnSectionを作成（RC矩形断面）
            column_section = ColumnSection.create_rectangle(
                width=width,  # X方向幅
                height=height,  # Y方向幅
            )

            # 既存のcreate_columnメソッドを使用（内部的にIfcColumnを作成）
            ifc_column = self.create_column(
                bottom_point=bottom_point,
                top_point=top_point,
                section=column_section,
                element_name=foundation_column_data["name"],
                element_tag=foundation_column_data.get(
                    "stb_section_name", f"FC_{foundation_column_data['name']}"
                ),
                element_guid=foundation_column_data["guid"],
                building_storey=building_storey,
                ifc_file=ifc_file,
            )

            # 基礎柱特有のプロパティを追加
            self._add_foundation_column_properties(
                ifc_column, foundation_column_data, ifc_file
            )

            logger.debug("基礎柱作成完了: %s", foundation_column_data.get("name", ""))
            return ifc_column
        except Exception as e:
            logger.error("基礎柱作成中にエラーが発生しました: %s", str(e))
            logger.error("基礎柱データ: %s", foundation_column_data)
            logger.error("エラー詳細", exc_info=True)
            return None

    def create_column(
        self,
        bottom_point: Point3D,
        top_point: Point3D,
        section: ColumnSection,
        element_name: str = "FoundationColumn",
        element_tag: str = None,
        element_guid: str = "",
        building_storey=None,
        ifc_file: ifcopenshell.file = None,
    ):
        """
        基礎柱をIfcColumnとして作成（既存実装を継承）

        Args:
            bottom_point: 底面中心点
            top_point: 頂面中心点
            section: 柱断面情報
            element_name: 要素名
            element_tag: 要素タグ
            element_guid: 要素GUID
            building_storey: IfcBuildingStorey
            ifc_file: IFCファイル

        Returns:
            作成されたIfcColumn
        """
        # 柱の幾何学計算
        column_geometry = self.geometry_calculator.calculate_column_geometry(
            bottom_point, top_point
        )

        # 柱の配置
        column_placement = self._create_standard_placement(column_geometry)

        # 柱タイプ作成
        column_type, _ = self.type_manager.create_element_type(section)

        # 形状作成
        shape_representation = self._create_standard_column_shape(
            section, section, column_geometry.height, False, 0.0
        )

        # 柱オブジェクト作成
        if element_tag is None:
            element_tag = f"FC_{element_name}"

        column = self._create_standard_structural_element_object(
            "IfcColumn",
            column_placement,
            shape_representation,
            element_name,
            element_tag,
            "COLUMN",
            element_guid,
        )

        # 関連付け
        self._associate_with_type(column, column_type)
        self._add_to_spatial_structure(column)  # プロパティ設定
        self._create_column_properties(
            column,
            bottom_point,
            top_point,
            section,
            section,
            column_geometry.height,
            False,
        )

        return column

    def _add_foundation_column_properties(
        self, ifc_column, foundation_column_data: dict, ifc_file: ifcopenshell.file
    ):
        """基礎柱特有のプロパティを追加（リファクタリング版）"""
        try:
            # property_managerが初期化されていない場合のフォールバック
            if self.property_manager is None:
                # 一時的なPropertyManagerを作成
                from ..utils.property_manager_base import ColumnPropertyManager

                temp_property_manager = ColumnPropertyManager(
                    ifc_file, self.project_builder.owner_history
                )
            else:
                temp_property_manager = self.property_manager

            # 基礎柱識別プロパティ
            basic_property_data = {
                "IsFoundationColumn": ("boolean", True),
                "FoundationColumnType": ("label", "RC_FOUNDATION_COLUMN"),
                "OriginalSTBType": ("label", "StbFoundationColumn"),
                "StructuralKind": ("label", foundation_column_data["kind_structure"]),
            }
            basic_props = temp_property_manager.create_structural_properties(
                basic_property_data
            )

            # FD部分の情報
            fd_section = foundation_column_data["fd_section"]
            fd_props = []
            if fd_section["section_info"]:
                fd_props = temp_property_manager.create_section_info_properties(
                    fd_section, "FD_"
                )
            else:
                fd_props = temp_property_manager.create_structural_properties(
                    {"FD_Section": ("label", "None (ID=0)")}
                )

            # WR部分の情報
            wr_props = []
            wr_section = foundation_column_data.get("wr_section")
            if wr_section:
                wr_props = temp_property_manager.create_section_info_properties(
                    wr_section, "WR_"
                )
                # プライマリセクションタイプを追加
                wr_props.extend(
                    temp_property_manager.create_structural_properties(
                        {"PrimarySectionType": ("label", "WR (Wall Rising)")}
                    )
                )
            else:
                wr_props = temp_property_manager.create_structural_properties(
                    {"PrimarySectionType": ("label", "FD (Foundation)")}
                )

            # 全プロパティを統合
            all_properties = basic_props + fd_props + wr_props

            # プロパティセットを作成して関連付け
            temp_property_manager._create_property_set(
                "STB_FoundationColumn_Properties", all_properties, ifc_column
            )

            logger.debug("基礎柱プロパティを追加しました")

        except Exception as e:
            logger.warning("基礎柱プロパティの追加中にエラーが発生しました: %s", str(e))

    def create_foundation_columns_from_data(
        self,
        foundation_columns_data: list,
        building_storey,
        ifc_file: ifcopenshell.file,
    ) -> list:
        """
        複数の基礎柱データからIfcColumnを一括作成

        Args:
            foundation_columns_data: 基礎柱データリスト
            building_storey: IfcBuildingStorey
            ifc_file: IFCファイル

        Returns:
            作成されたIfcColumnのリスト
        """
        # プロジェクト構造が初期化されていない場合は初期化
        if (
            self.profile_factory is None
            or self.geometry_builder is None
            or self.property_manager is None
        ):
            logger.warning("プロジェクト構造が未初期化のため、初期化を実行します")
            self.create_project_structure("基礎柱プロジェクト")

        created_columns = []

        for foundation_column_data in foundation_columns_data:
            try:
                ifc_column = self.create_foundation_column(
                    foundation_column_data, building_storey, ifc_file
                )
                if ifc_column:
                    created_columns.append(ifc_column)

            except Exception as e:
                logger.error("基礎柱作成中にエラー: %s", str(e))
                logger.error("基礎柱データ: %s", foundation_column_data)
                continue

        logger.info("基礎柱を %d 個作成しました", len(created_columns))
        return created_columns

    def _create_column_properties(
        self,
        column,
        bottom_point: Point3D,
        top_point: Point3D,
        sec_bottom: ColumnSection,
        sec_top: ColumnSection,
        height: float,
        is_tapered: bool,
    ):
        """柱のプロパティセットを作成"""
        # 共通プロパティ
        self._create_common_properties(column, "Pset_ColumnCommon")

        # 座標プロパティ
        self._create_column_coordinate_properties(
            column, bottom_point, top_point, height
        )

        # 断面プロパティ
        section_properties = self.property_manager.get_section_properties(
            sec_bottom, sec_top, is_tapered
        )

        if section_properties:
            pset_name = (
                "Pset_TaperedColumnSectionDimensions"
                if is_tapered
                else "Pset_ColumnSectionDimensions"
            )
            self.property_manager._create_property_set(
                pset_name, section_properties, column
            )
