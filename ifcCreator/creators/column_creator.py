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
                    definition, 0, "柱", StructuralSection,
                    bottom_section_key="sec_bottom",
                    top_section_key="sec_top"
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
            is_reference_direction = definition.get("is_reference_direction", False)
            return self.create_column(
                bottom_point,
                top_point,
                sec_bottom,
                sec_top,
                column_name,
                column_tag,
                stb_guid,
                rotate_radians,
                is_reference_direction,
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
            # デバッグ: 受け取った値を確認
            self.logger.debug(
                "create_column: %s, is_reference_direction=%s, rotate_radians=%.3f",
                column_name,
                is_reference_direction,
                rotate_radians,
            )
            
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
            if not self.project_builder or not self.project_builder.file:
                logger.warning(
                    "ProjectBuilder or IFC file not available for tapered column shape"
                )
                return None

            ifc_file = self.project_builder.file

            # 既存の柱プロファイル作成メソッドを使用
            bottom_profile = self._create_section_profile(bottom_section)
            top_profile = self._create_section_profile(top_section)

            if not bottom_profile or not top_profile:
                logger.error("Failed to create profiles for tapered column")
                return None

            # 梁のテーパーロジックを柱用に適用 - 旧版のUnifiedGeometryBuilderと同じロジック
            try:
                # 旧版の create_tapered_geometry メソッドを再現（柱用）
                shape_placement = ifc_file.createIfcAxis2Placement3D(
                    Location=ifc_file.createIfcCartesianPoint([0.0, 0.0, 0.0]),
                    Axis=ifc_file.createIfcDirection([0.0, 0.0, 1.0]),
                    RefDirection=ifc_file.createIfcDirection([1.0, 0.0, 0.0])
                )
                
                # IfcExtrudedAreaSolidTaperedで旧版と同じテーパー形状を作成
                solid = ifc_file.createIfcExtrudedAreaSolidTapered(
                    SweptArea=bottom_profile,
                    EndSweptArea=top_profile,
                    Position=shape_placement,
                    ExtrudedDirection=ifc_file.createIfcDirection([0.0, 0.0, 1.0]),
                    Depth=height,
                )
                
                logger.info(f"Created tapered column shape with IfcExtrudedAreaSolidTapered, height {height}")
                return solid
                
            except Exception as tapered_error:
                logger.warning(f"IfcExtrudedAreaSolidTapered creation failed: {tapered_error}, falling back to IfcSectionedSpine")
                
                # フォールバック: IfcSectionedSpineを使用
                try:
                    # スパインカーブ（柱の中心線）を作成
                    start_pt = ifc_file.createIfcCartesianPoint([0.0, 0.0, 0.0])
                    end_pt = ifc_file.createIfcCartesianPoint([0.0, 0.0, height])
                    spine_curve = ifc_file.createIfcPolyline([start_pt, end_pt])
                    
                    # 断面配置点
                    cross_section_positions = [
                        ifc_file.createIfcAxis2Placement3D(
                            Location=start_pt,
                            Axis=ifc_file.createIfcDirection([0.0, 0.0, 1.0]),
                            RefDirection=ifc_file.createIfcDirection([1.0, 0.0, 0.0])
                        ),
                        ifc_file.createIfcAxis2Placement3D(
                            Location=end_pt, 
                            Axis=ifc_file.createIfcDirection([0.0, 0.0, 1.0]),
                            RefDirection=ifc_file.createIfcDirection([1.0, 0.0, 0.0])
                        )
                    ]
                    
                    # 断面プロファイル
                    cross_sections = [bottom_profile, top_profile]
                    
                    # IfcSectionedSpineを作成
                    sectioned_spine = ifc_file.createIfcSectionedSpine(
                        SpineCurve=spine_curve,
                        CrossSections=cross_sections,
                        CrossSectionPositions=cross_section_positions
                    )
                    
                    logger.info(f"Created tapered column shape with IfcSectionedSpine fallback, height {height}")
                    return sectioned_spine
                    
                except Exception as spine_error:
                    logger.warning(f"IfcSectionedSpine creation also failed: {spine_error}, using simple extrusion")
                    
                    # 最終フォールバック: 下端断面での単純押し出し
                    direction = ifc_file.createIfcDirection([0.0, 0.0, 1.0])
                    shape_placement = ifc_file.createIfcAxis2Placement3D(
                        Location=ifc_file.createIfcCartesianPoint([0.0, 0.0, 0.0])
                    )
                    
                    solid = ifc_file.createIfcExtrudedAreaSolid(
                        SweptArea=bottom_profile,
                        Position=shape_placement,
                        ExtrudedDirection=direction,
                        Depth=height,
                    )
                    
                    logger.info(f"Created fallback column shape with bottom profile, height {height}")
                    return solid

        except Exception as e:
            logger.error(f"テーパー柱形状作成エラー: {e}")
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
            
            # section_typeを使用して断面タイプを判定
            section_type = getattr(section, 'section_type', 'UNKNOWN')
            
            # H形鋼の場合
            if section_type in ["H", "I"]:
                dimensions.update({
                    "height": getattr(section, 'overall_depth', getattr(section, 'height', 0.0)),
                    "width": getattr(section, 'overall_width', getattr(section, 'width', 0.0)),
                    "web_thickness": getattr(section, 'web_thickness', 0.0),
                    "flange_thickness": getattr(section, 'flange_thickness', 0.0)
                })
            
            # 角形鋼管の場合
            elif section_type in ["BOX", "BCR"]:
                dimensions.update({
                    "height": getattr(section, 'outer_height', getattr(section, 'height', 0.0)),
                    "width": getattr(section, 'outer_width', getattr(section, 'width', 0.0)),
                    "thickness": getattr(section, 'wall_thickness', 0.0)
                })
            
            # 円形鋼管の場合
            elif section_type in ["PIPE", "P"]:
                diameter = getattr(section, 'outer_diameter', getattr(section, 'diameter', 0.0))
                dimensions.update({
                    "diameter": diameter,
                    "thickness": getattr(section, 'wall_thickness', 0.0)
                })
            
            # L形鋼の場合
            elif section_type in ["L"]:
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
        """補間された寸法で断面プロファイルを作成（ProfileServiceを使用）"""
        try:
            # ProfileServiceを使用して統一的にプロファイルを作成
            from ..services.profile_service import ProfileService
            profile_service = ProfileService(self.project_builder.file)
            
            # 寸法情報を基にして一時的な断面オブジェクトを作成
            temp_section = type(base_section)(
                section_type=getattr(base_section, 'section_type', 'UNKNOWN'),
                **dimensions
            )
            
            return profile_service.create_profile(temp_section, "column")
            
        except Exception as e:
            self.logger.error(f"補間プロファイル作成エラー: {e}")
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

            # isReferenceDirectionによる回転処理（旧版と同様）
            # isReferenceDirection=false (H型配置): 90度回転を追加
            # isReferenceDirection=true (I型配置): 元の回転角度を維持
            effective_rotation = rotate_radians
            if not is_reference_direction:
                effective_rotation += math.pi / 2  # 90度（π/2ラジアン）追加でH型配置
                self.logger.debug(
                    "isReferenceDirection=false (H型配置): 回転角度を90度追加 (%.1f° -> %.1f°)",
                    math.degrees(rotate_radians),
                    math.degrees(effective_rotation),
                )
            else:
                self.logger.debug(
                    "isReferenceDirection=true (I型配置): 元の回転角度を維持 (%.1f°)",
                    math.degrees(rotate_radians),
                )

            # 回転角度に基づく参照方向（XY平面上のX軸回転）
            cos_val = math.cos(effective_rotation)
            sin_val = math.sin(effective_rotation)
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
        """断面プロファイルを作成（ProfileServiceを使用）"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            # ProfileServiceを使用してプロファイルを作成
            from ..services.profile_service import ProfileService
            profile_service = ProfileService(self.project_builder.file)
            return profile_service.create_profile(section, "column")

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
