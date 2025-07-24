"""Column Creator

v2.2.0 統合柱作成クラス
リファクタリング版をベースとした統一実装
BIMVision対応: 型定義・材料定義の関連付けを追加
"""

import math
from typing import Optional, Any, Dict
from .base_creator import LinearElementCreator
from ..utils.structural_section import StructuralSection
from ..utils.validator import Validator
from common.geometry import Point3D
from exceptions.custom_errors import ParameterValidationError, GeometryValidationError
import logging

logger = logging.getLogger(__name__)


class ColumnCreator(LinearElementCreator):
    """統合柱作成クラス

    v2.2.0: リファクタリング版の機能を統合した最終実装
    """

    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "column"
        self.validator = Validator()

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """柱要素を作成

        Args:
            definition: 柱定義辞書

        Returns:
            作成されたIFC柱要素
        """
        try:
            # DefinitionProcessorを使用して定義を処理（バリデーション前に処理）
            from common.definition_processor import DefinitionProcessor
            try:
                processed_def = DefinitionProcessor.process_vertical_element_definition(
                    definition, 0, "柱", StructuralSection
                )
                bottom_point = processed_def.get("bottom_point")
                top_point = processed_def.get("top_point")
                sec_bottom = processed_def.get("sec_bottom")
                sec_top = processed_def.get("sec_top")
                column_name = processed_def.get("name", "Column")
                column_tag = processed_def.get("tag", "C001")
                stb_guid = processed_def.get("stb_guid")
            except Exception as e:
                self.logger.error(f"柱定義の処理に失敗: {e}")
                return None

            # 処理後にバリデーション
            try:
                self.validator.validate_column_definition(processed_def)
            except ValueError as e:
                raise ParameterValidationError("柱", column_name, str(e)) from e

            # 断面情報の確認：section または sec_bottom のいずれかが必要
            section = processed_def.get("section")
            if not all([bottom_point, top_point]) or not (section or sec_bottom):
                self.logger.error(
                    f"柱 '{column_name}' の作成に必要な情報が不足しています（上下端座標または断面情報の不備）"
                )
                return None
            
            # 通常柱の場合はsectionをsec_bottomとして使用
            if section and not sec_bottom:
                sec_bottom = section
                sec_top = None  # 通常柱の場合はテーパーなし

            # 回転情報を取得
            rotate_radians = definition.get("rotate_radians", 0.0)
            is_ref_dir = definition.get("is_reference_direction", False)
            return self.create_column(
                bottom_point,
                top_point,
                sec_bottom,
                sec_top,
                column_name,
                column_tag,
                stb_guid,
                rotate_radians,
                is_ref_dir,
            )

        except Exception as e:
            self.logger.error(f"柱作成エラー: {e}")
            return None

    def create_column(
        self,
        bottom_point: Point3D,
        top_point: Point3D,
        sec_bottom: StructuralSection,
        sec_top: Optional[StructuralSection] = None,
        column_name: str = "Column",
        column_tag: str = "C001",
        stb_guid: Optional[str] = None,
        rotate_radians: float = 0.0,
        is_reference_direction: bool = False,
    ) -> Any:
        """柱を作成

        Args:
            bottom_point: 下端点
            top_point: 上端点
            sec_bottom: 下端断面
            sec_top: 上端断面（テーパー柱用）
            column_name: 柱名
            column_tag: 柱タグ
            stb_guid: STB GUID

        Returns:
            作成されたIFC柱要素
        """
        if not self.project_builder or not self.project_builder.file:
            self.logger.warning(
                "プロジェクトビルダーまたはIFCファイルが設定されていません"
            )
            return None

        try:
            # 上端断面の処理
            effective_top_section = sec_top or sec_bottom
            is_tapered = sec_top is not None and sec_bottom != effective_top_section

            # ジオメトリ作成
            shape, local_coord, center_point = self._create_column_geometry(
                bottom_point, top_point, sec_bottom, effective_top_section
            )

            if not shape:
                return None

            # 配置作成（回転適用）
            placement = self._create_placement(
                bottom_point, rotate_radians, is_reference_direction
            )

            # 柱オブジェクト作成
            column = self._create_column_object(
                placement, shape, column_name, column_tag, stb_guid
            )

            if column:
                # 型・材料関連付けを追加（BIMVision対応）
                self._associate_type_and_material(column, sec_bottom)

                # プロパティ設定
                self._set_column_properties(
                    column,
                    bottom_point,
                    top_point,
                    sec_bottom,
                    effective_top_section,
                    is_tapered,
                )

                self.logger.debug(f"柱 '{column_name}' を作成しました")

            return column

        except Exception as e:
            self.logger.error(f"柱作成中にエラー: {e}")
            return None

    def _associate_type_and_material(self, column, section: StructuralSection):
        """柱に型・材料を関連付け（BIMVision対応）"""
        try:
            if not hasattr(self.project_builder, "type_creator"):
                # 型・材料Creatorを初期化
                from .type_creator import TypeCreator
                from .material_creator import MaterialCreator

                self.project_builder.type_creator = TypeCreator(
                    self.project_builder.file, self.project_builder.owner_history
                )
                self.project_builder.material_creator = MaterialCreator(
                    self.project_builder.file, self.project_builder.owner_history
                )

            # プロファイル名を取得
            profile_name = getattr(section, "name", "Unknown")

            # 適切な型を取得・作成
            column_type = self.project_builder.type_creator.get_column_type_for_profile(
                profile_name
            )

            # 適切な材料を取得・作成
            material = self.project_builder.material_creator.get_material_for_profile(
                profile_name
            )

            # 関連付け
            self.project_builder.type_creator.relate_element_to_type(
                column, column_type
            )
            self.project_builder.material_creator.associate_material_to_elements(
                column, material
            )

            self.logger.debug(f"柱 {column.Name} に型・材料を関連付けました")

        except Exception as e:
            self.logger.error(f"型・材料関連付けエラー: {e}")
            # エラーが発生しても柱作成は続行

    def _create_column_geometry(
        self,
        bottom_point: Point3D,
        top_point: Point3D,
        bottom_section: StructuralSection,
        top_section: StructuralSection,
    ) -> tuple:
        """柱ジオメトリを作成"""
        try:
            # 柱の高さと方向を計算
            height = self._calculate_height(bottom_point, top_point)
            if height <= 0:
                self.logger.error("柱の高さが不正です")
                return None, None, None

            # ローカル座標系を作成（柱は垂直が基本）
            local_coord = self._create_local_coordinate_system(bottom_point, top_point)

            # 断面形状を作成
            if bottom_section == top_section:
                # 一定断面
                shape = self._create_uniform_column_shape(bottom_section, height)
            else:
                # テーパー断面
                shape = self._create_tapered_column_shape(
                    bottom_section, top_section, height
                )

            # 中心点を計算
            center_point = Point3D(
                (bottom_point.x + top_point.x) / 2,
                (bottom_point.y + top_point.y) / 2,
                (bottom_point.z + top_point.z) / 2,
            )

            return shape, local_coord, center_point

        except Exception as e:
            self.logger.error(f"柱ジオメトリ作成エラー: {e}")
            return None, None, None

    def _calculate_height(self, bottom_point: Point3D, top_point: Point3D) -> float:
        """柱の高さを計算"""
        dx = top_point.x - bottom_point.x
        dy = top_point.y - bottom_point.y
        dz = top_point.z - bottom_point.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _create_local_coordinate_system(
        self, bottom_point: Point3D, top_point: Point3D
    ):
        """ローカル座標系を作成"""
        # 簡易実装 - 実際の実装では詳細な座標変換が必要
        return None  # プレースホルダー

    def _create_uniform_column_shape(self, section: StructuralSection, height: float):
        """一定断面柱の形状を作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 断面プロファイルを作成
            profile = self._create_section_profile(section)
            if not profile:
                return None

            # 押し出し方向（柱の軸方向、通常はZ軸）
            direction = ifc_file.createIfcDirection(
                [0.0, 0.0, 1.0]
            )  # Z軸方向（柱の高さ方向）

            # 押し出し形状を部材ローカル原点に配置
            shape_placement = ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint([0.0, 0.0, 0.0])
            )
            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile,
                Position=shape_placement,
                ExtrudedDirection=direction,
                Depth=height,
            )

            return solid

        except Exception as e:
            self.logger.error(f"柱形状作成エラー: {e}")
            return None

    def _create_tapered_column_shape(
        self,
        bottom_section: StructuralSection,
        top_section: StructuralSection,
        height: float,
    ):
        """テーパー断面柱の形状を作成"""
        try:
            # 下端断面の形状を取得
            bottom_profile = self._create_section_profile(bottom_section)
            if not bottom_profile:
                self.logger.error("下端断面の形状作成に失敗")
                return None
            
            # 上端断面の形状を取得
            top_profile = self._create_section_profile(top_section)
            if not top_profile:
                self.logger.error("上端断面の形状作成に失敗")
                return None
            
            # テーパー押し出し形状を作成
            # 下端のプロファイルから上端のプロファイルへの線形変化
            direction = self.ifc.createIfcDirection((0.0, 0.0, 1.0))
            
            # IFC4.0以降のテーパー押し出し形状を作成
            # IfcSectionedSolidを使用してより精密なテーパー形状を作成
            try:
                # 軸線を作成（柱の中心軸）
                axis_points = [
                    self.ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                    self.ifc.createIfcCartesianPoint((0.0, 0.0, height))
                ]
                axis_curve = self.ifc.createIfcPolyline(axis_points)
                
                # 断面位置を定義（下端と上端）
                cross_sections = [bottom_profile, top_profile]
                cross_section_positions = [0.0, height]  # 軸線上の位置
                
                # IfcSectionedSolidHorizontal を作成（IFC4.0以降）
                sectioned_solid = self.ifc.createIfcSectionedSolidHorizontal(
                    Directrix=axis_curve,
                    CrossSections=cross_sections
                )
                
                return sectioned_solid
                
            except Exception as e:
                # フォールバック: 複数セグメントによる近似
                self.logger.warning(f"IfcSectionedSolidHorizontal作成に失敗、セグメント近似を使用: {e}")
                
                # 高さを10セグメントに分割（より滑らかな近似）
                segments = 10
                segment_height = height / segments
                solids = []
                
                for i in range(segments):
                    # 各セグメントの断面を線形補間で計算
                    ratio = i / segments
                    interpolated_profile = self._interpolate_section_profiles(
                        bottom_section, top_section, ratio
                    )
                    
                    if interpolated_profile:
                        # セグメントの押し出し
                        segment_solid = self.ifc.createIfcExtrudedAreaSolid(
                            SweptArea=interpolated_profile,
                            Position=self.ifc.createIfcAxis2Placement3D(
                                self.ifc.createIfcCartesianPoint((0.0, 0.0, i * segment_height)),
                                self.ifc.createIfcDirection((0.0, 0.0, 1.0)),
                                self.ifc.createIfcDirection((1.0, 0.0, 0.0))
                            ),
                            ExtrudedDirection=direction,
                            Depth=segment_height
                        )
                        solids.append(segment_solid)
                
                # 全セグメントをBoolean UNIONで結合
                if len(solids) > 1:
                    result_solid = solids[0]
                    for solid in solids[1:]:
                        boolean_result = self.ifc.createIfcBooleanResult(
                            Operator="UNION",
                            FirstOperand=result_solid,
                            SecondOperand=solid
                        )
                        result_solid = boolean_result
                    return result_solid
                elif len(solids) == 1:
                    return solids[0]
                
            return None
            
        except Exception as e:
            self.logger.error(f"テーパー断面柱形状作成エラー: {e}")
            return None

    def _interpolate_section_profiles(
        self,
        bottom_section: StructuralSection,
        top_section: StructuralSection,
        ratio: float
    ):
        """断面プロファイルの線形補間"""
        try:
            # 両断面の寸法を取得
            bottom_dims = self._get_section_dimensions(bottom_section)
            top_dims = self._get_section_dimensions(top_section)
            
            if not bottom_dims or not top_dims:
                return None
            
            # 寸法を線形補間
            interpolated_dims = {}
            for key in bottom_dims:
                if key in top_dims:
                    bottom_val = bottom_dims[key]
                    top_val = top_dims[key]
                    interpolated_dims[key] = bottom_val + (top_val - bottom_val) * ratio
            
            # 補間された寸法で新しい断面プロファイルを作成
            return self._create_interpolated_profile(bottom_section, interpolated_dims)
            
        except Exception as e:
            self.logger.error(f"断面プロファイル補間エラー: {e}")
            return None

    def _get_section_dimensions(self, section: StructuralSection) -> dict:
        """断面の寸法を取得"""
        try:
            dimensions = {}
            
            # H形鋼の場合
            if section.shape_name in ["H", "HW", "HM", "HN"]:
                dimensions.update({
                    "height": getattr(section, 'height', 0.0),
                    "width": getattr(section, 'width', 0.0),
                    "web_thickness": getattr(section, 'web_thickness', 0.0),
                    "flange_thickness": getattr(section, 'flange_thickness', 0.0)
                })
            
            # 角形鋼管の場合
            elif section.shape_name in ["BOX", "BCR"]:
                dimensions.update({
                    "height": getattr(section, 'height', 0.0),
                    "width": getattr(section, 'width', 0.0),
                    "thickness": getattr(section, 'thickness', 0.0)
                })
            
            # 円形鋼管の場合
            elif section.shape_name in ["PIPE", "P"]:
                dimensions.update({
                    "diameter": getattr(section, 'diameter', 0.0),
                    "thickness": getattr(section, 'thickness', 0.0)
                })
            
            # L形鋼の場合
            elif section.shape_name in ["L"]:
                dimensions.update({
                    "height": getattr(section, 'height', 0.0),
                    "width": getattr(section, 'width', 0.0),
                    "thickness": getattr(section, 'thickness', 0.0)
                })
            
            return dimensions
            
        except Exception as e:
            self.logger.error(f"断面寸法取得エラー: {e}")
            return {}

    def _create_interpolated_profile(self, base_section: StructuralSection, dimensions: dict):
        """補間された寸法で断面プロファイルを作成"""
        try:
            shape_name = base_section.shape_name
            
            # H形鋼の場合
            if shape_name in ["H", "HW", "HM", "HN"]:
                return self._create_h_profile(
                    dimensions.get("height", 0.0),
                    dimensions.get("width", 0.0),
                    dimensions.get("web_thickness", 0.0),
                    dimensions.get("flange_thickness", 0.0)
                )
            
            # 角形鋼管の場合
            elif shape_name in ["BOX", "BCR"]:
                return self._create_box_profile(
                    dimensions.get("height", 0.0),
                    dimensions.get("width", 0.0),
                    dimensions.get("thickness", 0.0)
                )
            
            # 円形鋼管の場合
            elif shape_name in ["PIPE", "P"]:
                return self._create_pipe_profile(
                    dimensions.get("diameter", 0.0),
                    dimensions.get("thickness", 0.0)
                )
            
            # L形鋼の場合
            elif shape_name in ["L"]:
                return self._create_l_profile(
                    dimensions.get("height", 0.0),
                    dimensions.get("width", 0.0),
                    dimensions.get("thickness", 0.0)
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"補間プロファイル作成エラー: {e}")
            return None

    def _create_h_profile(self, height: float, width: float, web_thickness: float, flange_thickness: float):
        """H形断面プロファイルを作成"""
        try:
            return self.ifc.createIfcIShapeProfileDef(
                ProfileType="AREA",
                ProfileName=f"H_{height}x{width}",
                OverallWidth=width,
                OverallDepth=height,
                WebThickness=web_thickness,
                FlangeThickness=flange_thickness,
                FilletRadius=None
            )
        except Exception as e:
            self.logger.error(f"H形プロファイル作成エラー: {e}")
            return None

    def _create_box_profile(self, height: float, width: float, thickness: float):
        """角形鋼管断面プロファイルを作成"""
        try:
            return self.ifc.createIfcRectangleHollowProfileDef(
                ProfileType="AREA",
                ProfileName=f"BOX_{height}x{width}x{thickness}",
                XDim=width,
                YDim=height,
                WallThickness=thickness,
                InnerFilletRadius=None,
                OuterFilletRadius=None
            )
        except Exception as e:
            self.logger.error(f"角形鋼管プロファイル作成エラー: {e}")
            return None

    def _create_pipe_profile(self, diameter: float, thickness: float):
        """円形鋼管断面プロファイルを作成"""
        try:
            return self.ifc.createIfcCircleHollowProfileDef(
                ProfileType="AREA",
                ProfileName=f"PIPE_{diameter}x{thickness}",
                Radius=diameter / 2.0,
                WallThickness=thickness
            )
        except Exception as e:
            self.logger.error(f"円形鋼管プロファイル作成エラー: {e}")
            return None

    def _create_l_profile(self, height: float, width: float, thickness: float):
        """L形断面プロファイルを作成"""
        try:
            return self.ifc.createIfcLShapeProfileDef(
                ProfileType="AREA",
                ProfileName=f"L_{height}x{width}x{thickness}",
                Depth=height,
                Width=width,
                Thickness=thickness,
                FilletRadius=None,
                EdgeRadius=None,
                LegSlope=None
            )
        except Exception as e:
            self.logger.error(f"L形プロファイル作成エラー: {e}")
            return None

    def _create_placement(
        self,
        bottom_point: Point3D,
        rotate_radians: float = 0.0,
        is_reference_direction: bool = False,
    ):
        """配置を作成（回転適用）"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 底面点を配置位置として使用
            location = ifc_file.createIfcCartesianPoint(
                [float(bottom_point.x), float(bottom_point.y), float(bottom_point.z)]
            )

            # Z軸は垂直方向
            axis = ifc_file.createIfcDirection([0.0, 0.0, 1.0])

            # 回転角度に基づく参照方向（XY平面上のX軸回転）
            cos_val = math.cos(rotate_radians)
            sin_val = math.sin(rotate_radians)
            ref_dir = ifc_file.createIfcDirection([cos_val, sin_val, 0.0])

            # 座標系を作成
            axis2placement = ifc_file.createIfcAxis2Placement3D(
                Location=location,
                Axis=axis,
                RefDirection=ref_dir,
            )
            return ifc_file.createIfcLocalPlacement(
                PlacementRelTo=None, RelativePlacement=axis2placement
            )

        except Exception as e:
            self.logger.error(f"配置作成エラー: {e}")
            return None

    def _create_column_object(
        self,
        placement,
        shape,
        column_name: str,
        column_tag: str,
        stb_guid: Optional[str],
    ):
        """柱オブジェクトを作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # GUIDを生成または変換
            from common.guid_utils import convert_stb_guid_to_ifc, create_ifc_guid

            try:
                if stb_guid:
                    # STB GUID を IFC 圧縮 GUID に変換
                    element_guid = convert_stb_guid_to_ifc(stb_guid)
                else:
                    element_guid = create_ifc_guid()
            except Exception:
                # 変換失敗時は新規 GUID を生成
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

            # IFC柱オブジェクトを作成
            column = ifc_file.createIfcColumn(
                GlobalId=element_guid,
                OwnerHistory=self.project_builder.owner_history,
                Name=column_name,
                Description=None,
                ObjectType=None,
                ObjectPlacement=placement,
                Representation=product_shape,
                Tag=column_tag,
            )

            return column

        except Exception as e:
            self.logger.error(f"柱オブジェクト作成エラー: {e}")
            return None

    def _create_section_profile(self, section: StructuralSection):
        """断面プロファイルを作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # sectionが辞書の場合とStructuralSectionオブジェクトの場合を両方サポートするヘルパー関数
            def get_section_property(key: str, default=None):
                if hasattr(section, 'properties'):
                    return section.properties.get(key, default)
                else:
                    return section.get(key, default)

            # 断面タイプを取得
            if hasattr(section, 'section_type'):
                section_type = section.section_type.upper()
            else:
                section_type = section.get("section_type", "RECTANGLE").upper()

            if section_type == "RECTANGLE":
                # 矩形断面 - STB抽出キー(width_x, width_y)に対応
                width = get_section_property("width_x", get_section_property("width", 300.0))
                height = get_section_property("width_y", get_section_property("height", 600.0))

                return ifc_file.createIfcRectangleProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"RECT_{width}x{height}",
                    XDim=width,
                    YDim=height,
                )

            elif section_type in ["H", "I", "IBEAM"]:
                # H形断面 - STB抽出キーに対応
                overall_width = get_section_property("overall_width", get_section_property("width", 200.0))
                overall_depth = get_section_property("overall_depth", get_section_property("height", 400.0))
                web_thickness = get_section_property("web_thickness", 8.0)
                flange_thickness = get_section_property("flange_thickness", 12.0)
                
                # プロファイル名の生成
                if hasattr(section, 'get_standardized_profile_name'):
                    profile_name = section.get_standardized_profile_name('legacy')
                else:
                    profile_name = f"H_{overall_width}x{overall_depth}x{web_thickness}x{flange_thickness}"

                return ifc_file.createIfcIShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=profile_name,
                    OverallWidth=overall_width,
                    OverallDepth=overall_depth,
                    WebThickness=web_thickness,
                    FlangeThickness=flange_thickness,
                )

            elif section_type == "CIRCLE":
                # 円形断面
                radius = get_section_property("radius", 150.0)

                return ifc_file.createIfcCircleProfileDef(
                    ProfileType="AREA", ProfileName=f"CIRCLE_{radius*2}", Radius=radius
                )

            elif section_type == "BOX":
                # 角形鋼管断面
                width = get_section_property("width", 200.0)
                height = get_section_property("height", 200.0)
                wall_thickness = get_section_property("wall_thickness", 8.0)

                return ifc_file.createIfcRectangleHollowProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"BOX_{width}x{height}x{wall_thickness}",
                    XDim=width,
                    YDim=height,
                    WallThickness=wall_thickness,
                )

            elif section_type == "PIPE":
                # 円形鋼管断面
                radius = get_section_property("radius", 100.0)
                wall_thickness = get_section_property("wall_thickness", 6.0)

                return ifc_file.createIfcCircleHollowProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"PIPE_{radius*2}x{wall_thickness}",
                    Radius=radius,
                    WallThickness=wall_thickness,
                )

            elif section_type == "C":
                # C形鋼（チャンネル）断面
                overall_depth = get_section_property("overall_depth", 250.0)
                flange_width = get_section_property("flange_width", 75.0)
                web_thickness = get_section_property("web_thickness", 4.5)
                flange_thickness = get_section_property("flange_thickness", 4.5)
                
                section_name = getattr(section, 'name', '') or get_section_property('stb_name', '')
                prof_name = (
                    section_name
                    or f"C_{overall_depth}x{flange_width}x{web_thickness}x{flange_thickness}"
                )

                return ifc_file.createIfcCShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Depth=overall_depth,
                    Width=flange_width,
                    WallThickness=web_thickness,
                    Girth=flange_thickness,
                )

            elif section_type == "COMPOUND_CHANNEL":
                # 複合チャンネル断面（2CB, 2CF等）
                overall_depth = get_section_property("overall_depth", 250.0)
                flange_width = get_section_property("flange_width", 75.0)
                web_thickness = get_section_property("web_thickness", 4.5)
                flange_thickness = get_section_property("flange_thickness", 4.5)
                arrangement = get_section_property("arrangement", "BACK_TO_BACK")
                
                section_name = getattr(section, 'name', '') or get_section_property('stb_name', '')
                prof_name = (
                    section_name
                    or f"2C_{arrangement}_{overall_depth}x{flange_width}x{web_thickness}x{flange_thickness}"
                )
                
                # 複合チャンネル断面は適切なIFCプロファイルタイプが無いため、
                # 組み合わされた断面として扱う
                # 単一C形鋼として近似し、全体幅を調整
                overall_width = get_section_property("overall_width", flange_width * 2)

                return ifc_file.createIfcCShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Depth=overall_depth,
                    Width=overall_width,
                    WallThickness=web_thickness,
                    Girth=flange_thickness,
                )

            elif section_type == "L":
                # L型鋼（アングル）断面
                width = get_section_property("width", 100.0)
                height = get_section_property("height", 100.0)
                thickness = get_section_property("thickness", 7.0)
                
                section_name = getattr(section, 'name', '') or get_section_property('stb_name', '')
                prof_name = (
                    section_name
                    or f"L_{width}x{height}x{thickness}"
                )

                return ifc_file.createIfcLShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Depth=height,
                    Width=width,
                    Thickness=thickness,
                )

            elif section_type == "T":
                # T形鋼断面
                overall_depth = get_section_property("overall_depth", 200.0)
                flange_width = get_section_property("flange_width", 150.0)
                web_thickness = get_section_property("web_thickness", 8.0)
                flange_thickness = get_section_property("flange_thickness", 12.0)
                
                section_name = getattr(section, 'name', '') or get_section_property('stb_name', '')
                prof_name = (
                    section_name
                    or f"T_{overall_depth}x{flange_width}x{web_thickness}x{flange_thickness}"
                )

                return ifc_file.createIfcTShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Depth=overall_depth,
                    FlangeWidth=flange_width,
                    WebThickness=web_thickness,
                    FlangeThickness=flange_thickness,
                )

            elif section_type == "CIRCLE":
                # 円形断面
                radius = get_section_property("radius", 150.0)
                
                return ifc_file.createIfcCircleProfileDef(
                    ProfileType="AREA", 
                    ProfileName=f"CIRCLE_{radius*2}", 
                    Position=None,
                    Radius=radius
                )

            else:
                # デフォルトは矩形断面
                self.logger.warning(
                    f"未対応の断面タイプ '{section_type}', 矩形断面で代用"
                )
                width = get_section_property("width", 300.0)
                height = get_section_property("height", 600.0)

                return ifc_file.createIfcRectangleProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"DEFAULT_RECT_{width}x{height}",
                    XDim=width,
                    YDim=height,
                )

        except Exception as e:
            self.logger.error(f"断面プロファイル作成エラー: {e}")
            return None

    def _set_column_properties(
        self,
        column,
        bottom_point: Point3D,
        top_point: Point3D,
        bottom_section: StructuralSection,
        top_section: StructuralSection,
        is_tapered: bool,
    ):
        """柱プロパティを設定"""
        try:
            # PropertyServiceを初期化
            from ..services.property_service import PropertyService
            property_service = PropertyService(self.project_builder.file)
            
            # プロパティ定義を作成
            definition = {
                'tag': column.Tag or '',
                'name': column.Name or '',
                'start_point': bottom_point,
                'end_point': top_point,
                'section': bottom_section
            }
            
            # プロパティセットを作成
            properties = property_service.create_element_properties(
                'column', definition, column
            )
            
            self.logger.debug(f"柱 {column.Name} に {len(properties)} 個のプロパティセットを作成しました")
            
        except Exception as e:
            self.logger.error(f"柱プロパティ設定エラー: {e}")
            # エラーが発生してもプロパティなしで続行

    @staticmethod
    def create_column_from_definition(definition: dict, index: int) -> Any:
        """定義辞書から柱を作成

        リファクタリング版との互換性のための静的メソッド
        """
        creator = ColumnCreator()
        return creator.create_element(definition)

    def create_columns(self, column_definitions: list) -> list:
        """複数の柱を作成

        Args:
            column_definitions: 柱定義のリスト

        Returns:
            作成された柱のリスト
        """
        return self.create_elements(column_definitions)
