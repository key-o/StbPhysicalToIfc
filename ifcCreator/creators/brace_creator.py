"""Brace Creator

v2.2.0 統合ブレース作成クラス
"""

import math
from typing import Optional, Any, Dict
from .base_creator import LinearElementCreator
from ..utils.structural_section import StructuralSection
from ..services.geometry_service import GeometryService
from ..creators.material_creator import MaterialCreator
from common.geometry import Point3D
import logging

logger = logging.getLogger(__name__)


class BraceCreator(LinearElementCreator):
    """統合ブレース作成クラス"""

    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "brace"
        self.logger = logger

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """ブレース要素を作成"""
        try:
            # 定義から必要パラメータを抽出
            start_point = definition.get("start_point")
            end_point = definition.get("end_point")

            # STBパーサーの出力形式に対応（section辞書からStructuralSectionを作成）
            section_data = definition.get("section")
            brace_section = None
            if section_data:
                # 重複を避けるため、name と section_type を除いた辞書を作成
                other_properties = {
                    k: v
                    for k, v in section_data.items()
                    if k not in ["stb_name", "section_type"]
                }
                brace_section = StructuralSection(
                    name=section_data.get("stb_name", ""),
                    section_type=section_data.get("section_type", ""),
                    **other_properties,
                )

            brace_name = definition.get("name", "Brace")
            brace_tag = definition.get("tag", "BR001")
            stb_guid = definition.get("stb_guid")

            # Point3Dオブジェクトの作成
            if start_point and isinstance(start_point, dict):
                start_point = Point3D(
                    start_point["x"], start_point["y"], start_point["z"]
                )
            if end_point and isinstance(end_point, dict):
                end_point = Point3D(end_point["x"], end_point["y"], end_point["z"])

            if not all([start_point, end_point, brace_section]):
                self.logger.error(
                    f"ブレース '{brace_name}' の作成に必要な情報が不足しています（座標または断面情報の不備）"
                )
                return None

            return self.create_brace(
                start_point, end_point, brace_section, brace_name, brace_tag, stb_guid
            )

        except Exception as e:
            self.logger.error(f"ブレース作成エラー: {e}")
            return None

    @staticmethod
    def create_brace_from_definition(definition: dict, index: int) -> Any:
        """定義辞書からブレースを作成"""
        creator = BraceCreator()
        return creator.create_element(definition)

    def create_brace(
        self,
        start_point: Point3D,
        end_point: Point3D,
        brace_section: StructuralSection,
        brace_name: str = "Brace",
        brace_tag: str = "BR001",
        stb_guid: Optional[str] = None,
    ) -> Any:
        """ブレースを作成

        Args:
            start_point: 開始点
            end_point: 終了点
            brace_section: ブレース断面
            brace_name: ブレース名
            brace_tag: ブレースタグ
            stb_guid: STB GUID

        Returns:
            作成されたIFCメンバー要素（ブレース）
        """
        if not self.project_builder or not self.project_builder.file:
            self.logger.warning(
                "プロジェクトビルダーまたはIFCファイルが設定されていません"
            )
            return None

        try:
            # ブレースの長さと方向を計算
            length = self._calculate_length(start_point, end_point)
            if length <= 0:
                self.logger.error("ブレースの長さが不正です")
                return None

            # ジオメトリ作成
            shape = self._create_brace_geometry(
                start_point, end_point, brace_section, length
            )

            if not shape:
                return None

            # 配置作成（Phase1強化: 精密配置計算）
            placement = self._create_placement(start_point, end_point, brace_section)

            # ブレースオブジェクト作成
            brace = self._create_brace_object(
                placement, shape, brace_name, brace_tag, stb_guid
            )

            if brace:
                # プロパティ設定
                self._set_brace_properties(brace, start_point, end_point, brace_section)
                
                # Phase2強化: MaterialProfile関連付け
                self._associate_material_profile(brace, brace_section, shape)
                
                self.logger.debug(f"ブレース '{brace_name}' を作成しました")

            return brace

        except Exception as e:
            self.logger.error(f"ブレース作成中にエラー: {e}")
            return None

    def _calculate_length(self, start_point: Point3D, end_point: Point3D) -> float:
        """ブレースの長さを計算"""
        dx = end_point.x - start_point.x
        dy = end_point.y - start_point.y
        dz = end_point.z - start_point.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _create_brace_geometry(
        self,
        start_point: Point3D,
        end_point: Point3D,
        brace_section: StructuralSection,
        length: float,
    ):
        """ブレースジオメトリを作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 断面プロファイルを作成
            profile = self._create_section_profile(brace_section)
            if not profile:
                return None

            # 旧版と同じアプローチ：押出開始点を長さの半分だけオフセット
            half_length = length / 2.0
            solid_origin_pt = ifc_file.createIfcCartesianPoint([0.0, 0.0, -half_length])

            # 押出方向と参照方向を設定（旧版に合わせる）
            extrude_dir = ifc_file.createIfcDirection([0.0, 0.0, 1.0])  # Z軸正方向
            ref_dir = ifc_file.createIfcDirection([1.0, 0.0, 0.0])  # X軸正方向

            # 押出配置
            shape_placement = ifc_file.createIfcAxis2Placement3D(
                Location=solid_origin_pt,
                Axis=extrude_dir,
                RefDirection=ref_dir,
            )

            # 押し出し実体を作成
            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile,
                Position=shape_placement,
                ExtrudedDirection=extrude_dir,
                Depth=length,
            )

            return solid

        except Exception as e:
            self.logger.error(f"ブレースジオメトリ作成エラー: {e}")
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

            if section_type == "L":
                # L形断面（アングル）
                overall_depth = get_section_property("overall_depth", 65.0)
                flange_width = get_section_property("flange_width", 65.0)
                web_thickness = get_section_property("web_thickness", 6.0)
                flange_thickness = get_section_property("flange_thickness", 6.0)

                return ifc_file.createIfcLShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"L_{overall_depth}x{flange_width}x{web_thickness}",
                    Depth=overall_depth,
                    Width=flange_width,
                    Thickness=web_thickness,
                    FilletRadius=get_section_property("internal_fillet_radius", 0.0),
                    EdgeRadius=None,
                    LegSlope=None,
                )

            elif section_type == "RECTANGLE":
                # 矩形断面
                width = get_section_property("width", 100.0)
                height = get_section_property("height", 100.0)

                return ifc_file.createIfcRectangleProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"RECT_{width}x{height}",
                    XDim=width,
                    YDim=height,
                )

            elif section_type in ["H", "I", "IBEAM"]:
                # H形断面
                overall_width = get_section_property("overall_width", 100.0)
                overall_depth = get_section_property("overall_depth", 100.0)
                web_thickness = get_section_property("web_thickness", 6.0)
                flange_thickness = get_section_property("flange_thickness", 8.0)

                # フィレット半径を取得（STBデータから、またはフランジ厚をデフォルト値として使用）
                fillet_radius = get_section_property(
                    "fillet_radius", flange_thickness
                )

                # 梁と同じプロファイル配置：深さ方向にオフセット
                half_depth = overall_depth / 2.0
                pos_point = ifc_file.createIfcCartesianPoint([0.0, -half_depth])
                position_2d = ifc_file.createIfcAxis2Placement2D(pos_point, None)

                # 統一プロファイル命名規則を使用
                # プロファイル名の生成
                if hasattr(section, 'get_standardized_profile_name'):
                    profile_name = section.get_standardized_profile_name('legacy')
                else:
                    profile_name = f"H_{overall_width}x{overall_depth}x{web_thickness}x{flange_thickness}"

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

            elif section_type == "BOX":
                # 角形鋼管断面
                width = get_section_property("width", 100.0)
                height = get_section_property("height", 100.0)
                wall_thickness = get_section_property("wall_thickness", 6.0)

                return ifc_file.createIfcRectangleHollowProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"BOX_{width}x{height}x{wall_thickness}",
                    XDim=width,
                    YDim=height,
                    WallThickness=wall_thickness,
                )

            elif section_type == "PIPE":
                # 円形鋼管断面
                radius = get_section_property("radius", 50.0)
                wall_thickness = get_section_property("wall_thickness", 4.0)

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
                overall_width = get_section_property(
                    "overall_width", flange_width * 2
                )

                return ifc_file.createIfcCShapeProfileDef(
                    ProfileType="AREA",
                    ProfileName=prof_name,
                    Depth=overall_depth,
                    Width=overall_width,
                    WallThickness=web_thickness,
                    Girth=flange_thickness,
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
                width = get_section_property("width", 100.0)
                height = get_section_property("height", 100.0)

                return ifc_file.createIfcRectangleProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"DEFAULT_RECT_{width}x{height}",
                    XDim=width,
                    YDim=height,
                )

        except Exception as e:
            self.logger.error(f"断面プロファイル作成エラー: {e}")
            return None

    def _create_placement(self, start_point: Point3D, end_point: Point3D, section=None):
        """配置を作成（Phase1強化: 精密配置計算）"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # Phase1強化: GeometryServiceの精密配置計算を使用
            self.logger.debug(f"ServiceContainer: {self.project_builder.service_container}")
            geometry_service = self.project_builder.service_container.get_service(
                GeometryService
            )
            self.logger.debug(f"GeometryService取得結果: {geometry_service}")
            if geometry_service:
                # 精密配置計算
                placement_info = geometry_service.create_structural_placement(
                    start_point, end_point, "BRACE"
                )

                self.logger.debug(f"ブレース精密配置計算成功: {placement_info}")

                # 軸方向・参照方向ベクトルを使用した精密配置
                location = ifc_file.createIfcCartesianPoint(
                    [
                        float(placement_info["origin"].x),
                        float(placement_info["origin"].y),
                        float(placement_info["origin"].z),
                    ]
                )

                # 軸方向ベクトル
                axis = ifc_file.createIfcDirection(placement_info["direction"])

                # 参照方向ベクトル
                ref_direction = ifc_file.createIfcDirection(
                    placement_info["ref_direction"]
                )

                # 精密な配置
                placement = ifc_file.createIfcAxis2Placement3D(
                    Location=location, Axis=axis, RefDirection=ref_direction
                )

                self.logger.debug(
                    f"ブレース精密配置: origin={placement_info['origin']}, "
                    f"axis={placement_info['direction']}, "
                    f"ref_direction={placement_info['ref_direction']}"
                )

                return ifc_file.createIfcLocalPlacement(
                    PlacementRelTo=None, RelativePlacement=placement  # 絶対配置
                )
            else:
                self.logger.warning(
                    "GeometryServiceが取得できません。フォールバック処理に移行します。"
                )

            # フォールバック: 従来の簡易配置
            # ブレースの開始点を配置位置として使用
            z_coord = float(start_point.z)

            # 梁せい方向（VDim）の半分をZ方向下げる（ブレースはYDim修正不要）
            if section:
                vdim = section.properties.get("overall_depth", 0.0)
                z_coord -= vdim / 2.0
                self.logger.debug(
                    f"ブレース VDim={vdim}mm, Z座標を{vdim/2.0}mm下げて調整: {z_coord}"
                )

            location = ifc_file.createIfcCartesianPoint(
                [float(start_point.x), float(start_point.y), z_coord]
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

    def _create_brace_object(
        self, placement, shape, brace_name: str, brace_tag: str, stb_guid: Optional[str]
    ):
        """ブレースオブジェクトを作成"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # GUIDを生成
            from common.guid_utils import create_ifc_guid

            element_guid = stb_guid if stb_guid else create_ifc_guid()

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

            # IFCメンバーオブジェクトを作成（ブレースはMemberとして扱う）
            member = ifc_file.createIfcMember(
                GlobalId=element_guid,
                OwnerHistory=self.project_builder.owner_history,
                Name=brace_name,
                Description=None,
                ObjectType=None,
                ObjectPlacement=placement,
                Representation=product_shape,
                Tag=brace_tag,
                PredefinedType="BRACE",  # ブレースタイプに設定
            )

            return member

        except Exception as e:
            self.logger.error(f"ブレースオブジェクト作成エラー: {e}")
            return None

    def _associate_material_profile(self, brace, brace_section: StructuralSection, profile):
        """ブレースにMaterialProfileを関連付け
        
        Phase2強化: 旧版TypeManagerBase._associate_materialの機能移植
        
        Args:
            brace: IFC要素（IfcMember）
            brace_section: ブレース断面情報
            profile: IFCプロファイル
        """
        try:
            if not self.project_builder or not self.project_builder.file:
                self.logger.warning("MaterialProfile関連付けにIFCファイルが必要です")
                return
                
            # MaterialCreatorをServiceContainerから取得
            material_creator = self.project_builder.service_container.get_service(
                MaterialCreator
            )
            if not material_creator:
                self.logger.warning("MaterialCreatorが取得できません")
                return
                
            # 断面タイプに基づいて材料を決定
            material = self._determine_brace_material(brace_section, material_creator)
            
            # MaterialProfileを作成
            profile_name = profile.ProfileName if hasattr(profile, 'ProfileName') else "BraceProfile"
            mat_profile = material_creator.create_material_profile(
                material=material,
                profile=profile,
                name=f"{profile_name}_MaterialProfile"
            )
            
            # MaterialProfileSetを作成  
            mat_profile_set = material_creator.create_material_profile_set(
                material_profiles=[mat_profile],
                name=f"{profile_name}_MaterialProfileSet"
            )
            
            # ブレースに材料を関連付け
            material_creator.associate_material_to_elements(
                elements=[brace],
                material=mat_profile_set
            )
            
            self.logger.debug(f"ブレースMaterialProfile関連付け完了: {material.Name}")
            
        except Exception as e:
            self.logger.error(f"MaterialProfile関連付けエラー: {e}")

    def _determine_brace_material(self, brace_section: StructuralSection, material_creator: MaterialCreator):
        """ブレース断面タイプに基づいて適切な材料を決定
        
        Args:
            brace_section: ブレース断面情報
            material_creator: 材料作成者
            
        Returns:
            IFC材料
        """
        section_type = brace_section.section_type.upper()
        
        # 鋼材系断面
        if section_type in ["L", "H", "I", "IBEAM", "BOX", "PIPE", "C", "T", "COMPOUND_CHANNEL"]:
            return material_creator.create_steel_material()
            
        # コンクリート系断面（矩形等）
        elif section_type in ["RECTANGLE"]:
            return material_creator.create_concrete_material()
            
        # デフォルトは鋼材（ブレースは主に鋼材）
        else:
            self.logger.debug(f"未知の断面タイプ '{section_type}', 鋼材を使用")
            return material_creator.create_steel_material()

    def _set_brace_properties(
        self,
        brace,
        start_point: Point3D,
        end_point: Point3D,
        brace_section: StructuralSection,
    ):
        """ブレースプロパティを設定
        
        Phase2強化: PropertyServiceを使用したブレースプロパティ設定
        """
        try:
            # PropertyServiceをServiceContainerから取得
            from ..services.property_service import PropertyService
            property_service = self.project_builder.service_container.get_service(
                PropertyService
            )
            if not property_service:
                self.logger.warning("PropertyServiceが取得できません")
                return
                
            # ブレース定義を構築
            brace_definition = {
                "tag": getattr(brace, "Tag", ""),
                "name": getattr(brace, "Name", ""),
                "start_point": start_point,
                "end_point": end_point,
                "section": brace_section,
            }
            
            # PropertyServiceでブレースプロパティを作成
            properties = property_service.create_element_properties(
                element_type="brace",
                definition=brace_definition,
                element_instance=brace,
                profile=None
            )
            
            self.logger.debug(f"ブレースプロパティ設定完了: {len(properties)}個のプロパティを作成")
            
        except Exception as e:
            self.logger.error(f"ブレースプロパティ設定エラー: {e}")

    def create_braces(self, brace_definitions: list) -> list:
        """複数のブレースを作成"""
        return self.create_elements(brace_definitions)
