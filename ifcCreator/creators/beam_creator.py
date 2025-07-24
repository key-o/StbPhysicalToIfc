"""Beam Creator

v2.2.0 統合梁作成クラス
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


class BeamCreator(LinearElementCreator):
    """統合梁作成クラス

    v2.2.0: リファクタリング版の機能を統合した最終実装
    """

    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "beam"
        self.validator = Validator()

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """梁要素を作成

        Args:
            definition: 梁定義辞書

        Returns:
            作成されたIFC梁要素
        """
        try:
            # パラメータ検証
            try:
                self.validator.validate_beam_definition(definition)
            except ValueError as e:
                beam_name = definition.get("name", "不明な梁")
                raise ParameterValidationError("梁", beam_name, str(e)) from e

            # 変断面梁対応: DefinitionProcessorを使用して定義を処理
            from common.definition_processor import DefinitionProcessor
            try:
                processed_def = DefinitionProcessor.process_linear_element_definition(
                    definition, 0, "梁", StructuralSection
                )
                sec_start = processed_def.get("sec_start")
                sec_end = processed_def.get("sec_end") 
                # 統一断面の場合は sec_start == sec_end なので、sec_end を None に設定
                if sec_start == sec_end:
                    sec_end = None
            except Exception as e:
                self.logger.error(f"梁定義の処理に失敗: {e}")
                return None
            # DefinitionProcessorから処理済み座標を取得
            start_point = processed_def.get("start_point")
            end_point = processed_def.get("end_point")
            
            beam_name = processed_def.get("name", "Beam")
            beam_tag = processed_def.get("tag", "B001")
            stb_guid = processed_def.get("stb_guid")

            if not all([start_point, end_point, sec_start]):
                self.logger.error(
                    f"梁 '{beam_name}' の作成に必要な情報が不足しています（座標または断面情報の不備）"
                )
                return None

            return self.create_beam(
                start_point,
                end_point,
                sec_start,
                sec_end,
                beam_name,
                beam_tag,
                stb_guid,
            )

        except Exception as e:
            self.logger.error(f"梁作成エラー: {e}")
            return None

    def create_beam(
        self,
        start_point: Point3D,
        end_point: Point3D,
        sec_start: StructuralSection,
        sec_end: Optional[StructuralSection] = None,
        beam_name: str = "Beam",
        beam_tag: str = "B001",
        stb_guid: Optional[str] = None,
    ) -> Any:
        """梁を作成

        Args:
            start_point: 開始点
            end_point: 終了点
            sec_start: 開始断面
            sec_end: 終了断面（テーパー梁用）
            beam_name: 梁名
            beam_tag: 梁タグ
            stb_guid: STB GUID

        Returns:
            作成されたIFC梁要素
        """
        if not self.project_builder or not self.project_builder.file:
            self.logger.warning(
                "プロジェクトビルダーまたはIFCファイルが設定されていません"
            )
            return None

        try:
            # 終了断面の処理
            effective_end_section = sec_end or sec_start
            is_tapered = sec_end is not None and sec_start != effective_end_section

            # ジオメトリ作成
            shape, local_coord, center_point = self._create_beam_geometry(
                start_point, end_point, sec_start, effective_end_section
            )

            if not shape:
                return None

            # 配置作成
            placement = self._create_placement(
                start_point, end_point, local_coord, sec_start
            )

            # 梁オブジェクト作成
            beam = self._create_beam_object(
                placement, shape, beam_name, beam_tag, stb_guid
            )

            if beam:
                # 型・材料関連付けを追加（BIMVision対応）
                self._associate_type_and_material(beam, sec_start)

                # プロパティ設定
                self._set_beam_properties(
                    beam,
                    start_point,
                    end_point,
                    sec_start,
                    effective_end_section,
                    is_tapered,
                )

                self.logger.debug(f"梁 '{beam_name}' を作成しました")

            return beam

        except Exception as e:
            self.logger.error(f"梁作成中にエラー: {e}")
            return None

    def _associate_type_and_material(self, beam, section: StructuralSection):
        """梁に型・材料を関連付け（BIMVision対応）"""
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
            beam_type = self.project_builder.type_creator.get_beam_type_for_profile(
                profile_name
            )

            # 適切な材料を取得・作成
            material = self.project_builder.material_creator.get_material_for_profile(
                profile_name
            )

            # 関連付け
            self.project_builder.type_creator.relate_element_to_type(beam, beam_type)
            self.project_builder.material_creator.associate_material_to_elements(
                beam, material
            )

            self.logger.debug(f"梁 {beam.Name} に型・材料を関連付けました")

        except Exception as e:
            self.logger.error(f"型・材料関連付けエラー: {e}")
            # エラーが発生しても梁作成は続行

    def _create_beam_geometry(
        self,
        start_point: Point3D,
        end_point: Point3D,
        start_section: StructuralSection,
        end_section: StructuralSection,
    ) -> tuple:
        """梁ジオメトリを作成"""
        try:
            # 梁の長さと方向を計算
            length = self._calculate_length(start_point, end_point)
            if length <= 0:
                self.logger.error("梁の長さが不正です")
                return None, None, None

            # ローカル座標系を作成
            local_coord = self._create_local_coordinate_system(start_point, end_point)
            if not local_coord:
                self.logger.error("ローカル座標系作成に失敗しました")
                return None, None, None

            # 断面形状を作成
            if start_section == end_section:
                # 一定断面
                shape = self._create_uniform_beam_shape(
                    start_section, local_coord, length
                )
            else:
                # テーパー断面
                shape = self._create_tapered_beam_shape(
                    start_section, end_section, length
                )

            # 中心点を計算
            center_point = Point3D(
                (start_point.x + end_point.x) / 2,
                (start_point.y + end_point.y) / 2,
                (start_point.z + end_point.z) / 2,
            )

            return shape, local_coord, center_point

        except Exception as e:
            self.logger.error(f"梁ジオメトリ作成エラー: {e}")
            return None, None, None

    def _calculate_length(self, start_point: Point3D, end_point: Point3D) -> float:
        """梁の長さを計算"""
        dx = end_point.x - start_point.x
        dy = end_point.y - start_point.y
        dz = end_point.z - start_point.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _create_local_coordinate_system(self, start_point: Point3D, end_point: Point3D):
        """ローカル座標系を作成"""
        try:
            # 梁の方向ベクトルを計算
            direction_x = end_point.x - start_point.x
            direction_y = end_point.y - start_point.y
            direction_z = end_point.z - start_point.z

            # 正規化
            length = math.sqrt(direction_x**2 + direction_y**2 + direction_z**2)
            if length == 0:
                return None

            beam_axis = [
                direction_x / length,
                direction_y / length,
                direction_z / length,
            ]

            # 梁のプロファイル配置用座標系を作成
            # - beam_axis: 梁軸方向（押し出し方向）
            # - up_vector: 構造上の上向き（プロファイルの上下を決める）
            # - side_vector: 梁軸×上向きの外積（プロファイルの左右を決める）

            up_vector = [0.0, 0.0, 1.0]  # 構造上の上向き（グローバルZ軸）

            # 旧版と同じ参照方向計算方式に統一
            # StructuralGeometryCalculator._calculate_beam_reference_direction と同一ロジック
            if abs(beam_axis[0]) < 1e-6 and abs(beam_axis[1]) < 1e-6:
                # 梁が鉛直（Z軸方向）の場合
                side_vector = [1.0, 0.0, 0.0]
            else:
                # 水平梁の場合、旧版と同じ計算式
                ref_x = -beam_axis[1]
                ref_y = beam_axis[0]
                ref_z = 0.0
                
                # ベクトルの正規化
                side_length = math.sqrt(ref_x * ref_x + ref_y * ref_y + ref_z * ref_z)
                if side_length > 1e-6:
                    side_vector = [ref_x / side_length, ref_y / side_length, ref_z / side_length]
                else:
                    side_vector = [1.0, 0.0, 0.0]

            # IFCプロファイル配置用の座標系
            # Axis: 押し出し方向（梁軸）
            # RefDirection: プロファイル内でのX方向（通常は水平方向）
            profile_coord = {
                "extrusion_axis": beam_axis,  # 押し出し方向
                "ref_direction": side_vector,  # プロファイルのX方向
                "up_direction": up_vector,  # プロファイルのY方向（上向き）
            }

            return profile_coord

        except Exception as e:
            self.logger.error(f"ローカル座標系作成エラー: {e}")
            return None

    def _create_uniform_beam_shape(
        self, section: StructuralSection, local_coord: Dict[str, Any], length: float
    ):
        """一定断面梁の形状を作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 断面プロファイルを作成
            profile = self._create_section_profile(section)
            if not profile:
                return None

            logger.debug(f"梁形状を作成中: プロファイル={profile.ProfileName}")

            # 旧版と同じアプローチ：押出開始点を長さの半分だけオフセット
            half_length = length / 2.0
            
            solid_origin_pt = ifc_file.createIfcCartesianPoint([0.0, 0.0, -half_length])

            # 押出方向と参照方向を設定（旧版に合わせる）
            extrude_dir = ifc_file.createIfcDirection([0.0, 0.0, 1.0])  # Z軸正方向
            ref_dir = ifc_file.createIfcDirection(
                [1.0, 0.0, 0.0]
            )  # X軸正方向（梁軸方向）

            # 押出配置
            shape_placement = ifc_file.createIfcAxis2Placement3D(
                Location=solid_origin_pt,
                Axis=extrude_dir,
                RefDirection=ref_dir,
            )

            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile,
                Position=shape_placement,
                ExtrudedDirection=extrude_dir,
                Depth=length,
            )

            return solid

        except Exception as e:
            self.logger.error(f"梁形状作成エラー: {e}")
            return None

    def _create_tapered_beam_shape(
        self,
        start_section: StructuralSection,
        end_section: StructuralSection,
        length: float,
    ):
        """テーパー断面梁の形状を作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                logger.warning(
                    "ProjectBuilder or IFC file not available for tapered beam shape"
                )
                return None

            ifc_file = self.project_builder.file

            # 既存の梁プロファイル作成メソッドを使用（上中央基準で作成済み）
            start_profile = self._create_section_profile(start_section)
            end_profile = self._create_section_profile(end_section)

            if not start_profile or not end_profile:
                logger.error("Failed to create profiles for tapered beam")
                return None

            # テーパー形状作成 - 旧実装のUnifiedGeometryBuilderロジックを参考
            # IFC4でのテーパー形状はIfcSectionedSpineまたはIfcSweptAreaSolidTaperedを使用
            
            # IfcSectionedSpineを使用したテーパー形状作成
            try:
                # スパインカーブ（梁の中心線）を作成
                start_pt = ifc_file.createIfcCartesianPoint([0.0, 0.0, 0.0])
                end_pt = ifc_file.createIfcCartesianPoint([length, 0.0, 0.0])
                spine_curve = ifc_file.createIfcPolyline([start_pt, end_pt])
                
                # 断面配置点
                cross_section_positions = [
                    ifc_file.createIfcAxis2Placement3D(
                        Location=start_pt,
                        Axis=ifc_file.createIfcDirection([0.0, 0.0, 1.0]),
                        RefDirection=ifc_file.createIfcDirection([0.0, 1.0, 0.0])
                    ),
                    ifc_file.createIfcAxis2Placement3D(
                        Location=end_pt, 
                        Axis=ifc_file.createIfcDirection([0.0, 0.0, 1.0]),
                        RefDirection=ifc_file.createIfcDirection([0.0, 1.0, 0.0])
                    )
                ]
                
                # 断面プロファイル
                cross_sections = [start_profile, end_profile]
                
                # IfcSectionedSpineを作成
                sectioned_spine = ifc_file.createIfcSectionedSpine(
                    SpineCurve=spine_curve,
                    CrossSections=cross_sections,
                    CrossSectionPositions=cross_section_positions
                )
                
                logger.info(f"Created tapered beam shape with IfcSectionedSpine, length {length}")
                return sectioned_spine
                
            except Exception as spine_error:
                logger.warning(f"IfcSectionedSpine creation failed: {spine_error}, falling back to simple extrusion")
                
                # フォールバック: 開始断面での単純押し出し
                direction = ifc_file.createIfcDirection([1.0, 0.0, 0.0])
                shape_placement = ifc_file.createIfcAxis2Placement3D(
                    Location=ifc_file.createIfcCartesianPoint([0.0, 0.0, 0.0])
                )
                
                solid = ifc_file.createIfcExtrudedAreaSolid(
                    SweptArea=start_profile,
                    Position=shape_placement,
                    ExtrudedDirection=direction,
                    Depth=length,
                )
                
                logger.info(f"Created fallback beam shape with start profile, length {length}")
                return solid

        except Exception as e:
            logger.error(f"テーパー梁形状作成エラー: {e}")
            return None

    def _create_placement(
        self, start_point: Point3D, end_point: Point3D, local_coord, section=None
    ):
        """配置を作成 - 旧版StructuralGeometryCalculator方式に完全準拠"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None
            ifc_file = self.project_builder.file

            # 旧版と完全に同じ計算方式を使用
            # StructuralGeometryCalculator._calculate_base_geometry と同一ロジック
            center_x = (start_point.x + end_point.x) / 2
            center_y = (start_point.y + end_point.y) / 2
            center_z = (start_point.z + end_point.z) / 2
            
            # はりせい調整は一切行わない（旧版準拠）
            # geometry.center.to_list() の結果と同等の座標を使用

            # 中心点を配置位置として使用
            location = ifc_file.createIfcCartesianPoint([center_x, center_y, center_z])

            # 旧版の配置方式: geometry.direction と geometry.reference_direction を使用
            # local_coordから方向ベクトルを取得（旧版計算済み）
            axis = ifc_file.createIfcDirection(local_coord["extrusion_axis"])
            ref_direction = ifc_file.createIfcDirection(local_coord["ref_direction"])

            # 旧版と同じ配置作成
            axis2placement = ifc_file.createIfcAxis2Placement3D(
                Location=location, Axis=axis, RefDirection=ref_direction
            )
            return ifc_file.createIfcLocalPlacement(
                PlacementRelTo=self.project_builder.storey_placement,
                RelativePlacement=axis2placement,
            )
        except Exception as e:
            self.logger.error(f"配置作成エラー: {e}")
            return None

    def _create_beam_object(
        self, placement, shape, beam_name: str, beam_tag: str, stb_guid: Optional[str]
    ):
        """梁オブジェクトを作成"""
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

            # IFC梁オブジェクトを作成
            beam = ifc_file.createIfcBeam(
                GlobalId=element_guid,
                OwnerHistory=self.project_builder.owner_history,
                Name=beam_name,
                Description=None,
                ObjectType=None,
                ObjectPlacement=placement,
                Representation=product_shape,
                Tag=beam_tag,
            )

            # 梁作成完了をデバッグログに記録
            logger.debug(f"梁を作成しました: 名前={beam_name}, GUID={element_guid}")
            return beam

        except Exception as e:
            self.logger.error(f"梁オブジェクト作成エラー: {e}")
            return None

    def _create_section_profile(self, section: StructuralSection):
        """断面プロファイルを作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 断面タイプに基づいてプロファイルを作成
            section_type = section.section_type.upper()

            if section_type == "RECTANGLE":
                # 矩形断面
                width = section.properties.get("width", 300.0)
                height = section.properties.get("height", 600.0)
                
                # 旧版align_top_center=True相当：上中央基準に調整
                half_height = height / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_height])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcRectangleProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"RECT_{width}x{height}",
                    Position=position_2d,
                    XDim=width,
                    YDim=height,
                )

            elif section_type in ["H", "I", "IBEAM"]:
                # H形断面
                overall_width = section.properties.get("overall_width", 200.0)
                overall_depth = section.properties.get("overall_depth", 400.0)
                web_thickness = section.properties.get("web_thickness", 8.0)
                flange_thickness = section.properties.get("flange_thickness", 12.0)
                # プロファイル名を STB 名またはパラメータで設定
                prof_name = (
                    section.name
                    or f"H_{overall_depth}x{overall_width}x{web_thickness}x{flange_thickness}"
                )
                # 旧実装に合わせてプロファイルを深さ方向にオフセット
                half_depth = overall_depth / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_depth])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)
                # フィレット半径を取得（STBデータから、またはフランジ厚をデフォルト値として使用）
                fillet_radius = section.properties.get(
                    "fillet_radius", flange_thickness
                )

                # 統一プロファイル命名規則を使用
                profile_name = section.get_standardized_profile_name("legacy")

                return ifc_file.createIfcIShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=profile_name,
                    Position=position_2d,
                    OverallWidth=overall_width,
                    OverallDepth=overall_depth,
                    WebThickness=web_thickness,
                    FlangeThickness=flange_thickness,
                    FilletRadius=fillet_radius,
                )

            elif section_type == "CIRCLE":
                # 円形断面
                radius = section.properties.get("radius", 150.0)
                
                # 旧版align_top_center=True相当：上中央基準に調整
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -radius])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcCircleProfileDef(
                    ProfileType="AREA", 
                    ProfileName=f"CIRCLE_{radius*2}", 
                    Position=position_2d,
                    Radius=radius
                )

            elif section_type == "BOX":
                # 角形鋼管断面
                width = section.properties.get("width", 200.0)
                height = section.properties.get("height", 200.0)
                wall_thickness = section.properties.get("wall_thickness", 8.0)
                
                # 旧版align_top_center=True相当：上中央基準に調整
                half_height = height / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_height])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcRectangleHollowProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"BOX_{width}x{height}x{wall_thickness}",
                    Position=position_2d,
                    XDim=width,
                    YDim=height,
                    WallThickness=wall_thickness,
                )

            elif section_type == "PIPE":
                # 円形鋼管断面
                radius = section.properties.get("radius", 100.0)
                wall_thickness = section.properties.get("wall_thickness", 6.0)
                
                # 旧版align_top_center=True相当：上中央基準に調整
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -radius])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcCircleHollowProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"PIPE_{radius*2}x{wall_thickness}",
                    Position=position_2d,
                    Radius=radius,
                    WallThickness=wall_thickness,
                )

            elif section_type == "C":
                # C形鋼（チャンネル）断面
                overall_depth = section.properties.get("overall_depth", 250.0)
                flange_width = section.properties.get("flange_width", 75.0)
                web_thickness = section.properties.get("web_thickness", 4.5)
                flange_thickness = section.properties.get("flange_thickness", 4.5)

                prof_name = (
                    section.name
                    or f"C_{overall_depth}x{flange_width}x{web_thickness}x{flange_thickness}"
                )
                
                # 旧版align_top_center=True相当：上中央基準に調整
                half_depth = overall_depth / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_depth])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcCShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Position=position_2d,
                    Depth=overall_depth,
                    Width=flange_width,
                    WallThickness=web_thickness,
                    Girth=flange_thickness,
                )

            elif section_type == "COMPOUND_CHANNEL":
                # 複合チャンネル断面（2CB, 2CF等）
                overall_depth = section.properties.get("overall_depth", 250.0)
                flange_width = section.properties.get("flange_width", 75.0)
                web_thickness = section.properties.get("web_thickness", 4.5)
                flange_thickness = section.properties.get("flange_thickness", 4.5)
                arrangement = section.properties.get("arrangement", "BACK_TO_BACK")

                prof_name = (
                    section.name
                    or f"2C_{arrangement}_{overall_depth}x{flange_width}x{web_thickness}x{flange_thickness}"
                )

                # 複合チャンネル断面は適切なIFCプロファイルタイプが無いため、
                # 組み合わされた断面として扱う
                # 単一C形鋼として近似し、全体幅を調整
                overall_width = section.properties.get(
                    "overall_width", flange_width * 2
                )
                
                # 旧版align_top_center=True相当：上中央基準に調整
                half_depth = overall_depth / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_depth])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcCShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Position=position_2d,
                    Depth=overall_depth,
                    Width=overall_width,
                    WallThickness=web_thickness,
                    Girth=flange_thickness,
                )

            elif section_type == "L":
                # L型鋼（アングル）断面
                width = section.properties.get("width", 100.0)
                height = section.properties.get("height", 100.0)
                thickness = section.properties.get("thickness", 7.0)

                prof_name = section.name or f"L_{width}x{height}x{thickness}"
                
                # 旧版align_top_center=True相当：上中央基準に調整
                half_height = height / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_height])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcLShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Position=position_2d,
                    Depth=height,
                    Width=width,
                    Thickness=thickness,
                )

            elif section_type == "T":
                # T形鋼断面
                overall_depth = section.properties.get("overall_depth", 200.0)
                flange_width = section.properties.get("flange_width", 150.0)
                web_thickness = section.properties.get("web_thickness", 8.0)
                flange_thickness = section.properties.get("flange_thickness", 12.0)

                prof_name = (
                    section.name
                    or f"T_{overall_depth}x{flange_width}x{web_thickness}x{flange_thickness}"
                )
                
                # 旧版align_top_center=True相当：上中央基準に調整
                half_depth = overall_depth / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_depth])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcTShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Position=position_2d,
                    Depth=overall_depth,
                    FlangeWidth=flange_width,
                    WebThickness=web_thickness,
                    FlangeThickness=flange_thickness,
                )

            else:
                # デフォルトは矩形断面
                self.logger.warning(
                    f"未対応の断面タイプ '{section_type}', 矩形断面で代用"
                )
                width = section.properties.get("width", 300.0)
                height = section.properties.get("height", 600.0)
                
                # 旧版align_top_center=True相当：上中央基準に調整
                half_height = height / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_height])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                return ifc_file.createIfcRectangleProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"DEFAULT_RECT_{width}x{height}",
                    Position=position_2d,
                    XDim=width,
                    YDim=height,
                )

        except Exception as e:
            self.logger.error(f"断面プロファイル作成エラー: {e}")
            return None

    def _set_beam_properties(
        self,
        beam,
        start_point: Point3D,
        end_point: Point3D,
        start_section: StructuralSection,
        end_section: StructuralSection,
        is_tapered: bool,
    ):
        """梁プロパティを設定"""
        try:
            # PropertyServiceを初期化
            from ..services.property_service import PropertyService

            property_service = PropertyService(self.project_builder.file)

            # プロパティ定義を作成
            definition = {
                "tag": beam.Tag or "",
                "name": beam.Name or "",
                "start_point": start_point,
                "end_point": end_point,
                "section": start_section,
            }

            # プロパティセットを作成
            properties = property_service.create_element_properties(
                "beam", definition, beam
            )

            self.logger.debug(
                f"梁 {beam.Name} に {len(properties)} 個のプロパティセットを作成しました"
            )

        except Exception as e:
            self.logger.error(f"梁プロパティ設定エラー: {e}")
            # エラーが発生してもプロパティなしで続行

    @staticmethod
    def create_beam_from_definition(definition: dict, index: int) -> Any:
        """定義辞書から梁を作成

        リファクタリング版との互換性のための静的メソッド
        """
        creator = BeamCreator()
        return creator.create_element(definition)

    def create_beams(self, beam_definitions: list) -> list:
        """複数の梁を作成

        Args:
            beam_definitions: 梁定義のリスト

        Returns:
            作成された梁のリスト
        """
        return self.create_elements(beam_definitions)
