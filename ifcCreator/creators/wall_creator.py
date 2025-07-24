"""Wall Creator

v2.2.0 統合壁作成クラス
"""

from typing import Optional, Any, Dict, List
from .base_creator import PlanarElementCreator
from ..utils.structural_section import StructuralSection
from ..utils.validator import Validator
from common.geometry import Point3D
from exceptions.custom_errors import ParameterValidationError, GeometryValidationError
import logging
import math

logger = logging.getLogger(__name__)


class WallCreator(PlanarElementCreator):
    """統合壁作成クラス"""

    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "wall"
        self.validator = Validator()

    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """壁要素を作成"""
        try:
            # パラメータ検証
            try:
                self.validator.validate_wall_definition(definition)
            except ValueError as e:
                wall_name = definition.get("name", "不明な壁")
                raise ParameterValidationError("壁", wall_name, str(e)) from e
            
            # 定義から必要パラメータを抽出
            corner_nodes = definition.get("corner_nodes")
            center_point = definition.get("center_point")
            openings = definition.get("openings", [])

            # STBパーサーの出力形式に対応（section辞書からStructuralSectionを作成）
            section_data = definition.get("section")
            wall_section = None
            if section_data:
                # 重複を避けるため、name と section_type を除いた辞書を作成
                other_properties = {
                    k: v
                    for k, v in section_data.items()
                    if k not in ["stb_name", "section_type"]
                }
                wall_section = StructuralSection(
                    name=section_data.get("stb_name", ""),
                    section_type=section_data.get("section_type", ""),
                    **other_properties,
                )

            wall_name = definition.get("name", "Wall")
            wall_tag = definition.get("tag", "W001")
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

            if not all([corner_points, wall_section]):
                self.logger.error(
                    f"壁 '{wall_name}' の作成に必要な情報が不足しています（平面形状または断面情報の不備）"
                )
                return None

            return self.create_wall(
                corner_points,
                wall_section,
                center_point,
                openings,
                wall_name,
                wall_tag,
                stb_guid,
            )

        except Exception as e:
            self.logger.error(f"壁作成エラー: {e}")
            return None

    @staticmethod
    def create_wall_from_definition(definition: dict, index: int) -> Any:
        """定義辞書から壁を作成"""
        creator = WallCreator()
        return creator.create_element(definition)

    def create_wall(
        self,
        corner_points: List[Point3D],
        wall_section: StructuralSection,
        center_point: Optional[Point3D] = None,
        openings: List[Dict] = None,
        wall_name: str = "Wall",
        wall_tag: str = "W001",
        stb_guid: Optional[str] = None,
    ) -> Any:
        """壁を作成

        Args:
            corner_points: 角点のリスト
            wall_section: 壁断面
            center_point: 中心点（オプション）
            openings: 開口部のリスト
            wall_name: 壁名
            wall_tag: 壁タグ
            stb_guid: STB GUID

        Returns:
            作成されたIFC壁要素
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
                self.logger.debug(f"壁 '{wall_name}' の配置に提供された中心点を使用: ({center_point.x:.1f}, {center_point.y:.1f}, {center_point.z:.1f})")
            else:
                # center_pointが提供されていない場合は角点から計算
                effective_center = self._calculate_center_from_corners(corner_points)
                self.logger.debug(f"壁 '{wall_name}' の配置に計算された中心点を使用: ({effective_center.x:.1f}, {effective_center.y:.1f}, {effective_center.z:.1f})")

            # 壁のジオメトリ作成（ローカル座標系）
            shape, local_coord = self._create_wall_geometry(corner_points, wall_section, openings, effective_center)

            if not shape:
                return None

            # 配置作成（面の法線方向を考慮）
            placement = self._create_placement(effective_center, local_coord)

            # 壁オブジェクト作成
            wall = self._create_wall_object(
                placement, shape, wall_name, wall_tag, stb_guid
            )

            if wall:
                # プロパティ設定
                self._set_wall_properties(wall, corner_points, wall_section, openings)
                
                # 開口部がある場合、開口要素を作成
                if openings:
                    self._create_wall_openings(
                        wall, openings, wall_section, local_coord
                    )
                
                self.logger.debug(f"壁 '{wall_name}' を作成しました")

            return wall

        except Exception as e:
            self.logger.error(f"壁作成中にエラー: {e}")
            return None

    def _create_wall_geometry(
        self,
        corner_points: List[Point3D],
        wall_section: StructuralSection,
        openings: List[Dict] = None,
        center_point: Point3D = None,
    ):
        """壁ジオメトリを作成（ローカル座標系）"""
        try:
            if not self.project_builder or not self.project_builder.file:
                return None

            ifc_file = self.project_builder.file

            # 角点からポリゴンを作成（3点以上想定、4点未満の場合は拡張）
            if len(corner_points) < 3:
                self.logger.error("壁には最低3つの角点が必要です")
                return None, None
            
            # 3点の場合は4点に拡張（最初の点を複製）
            if len(corner_points) == 3:
                corner_points = corner_points + [corner_points[0]]
                self.logger.debug("3点の壁を4点に拡張しました")

            # 中心点を計算（未提供の場合）
            if not center_point:
                center_point = self._calculate_center_from_corners(corner_points)

            # 角点を辞書形式に変換（面の法線計算のため）
            corner_nodes = []
            for point in corner_points[:4]:
                corner_nodes.append({"x": point.x, "y": point.y, "z": point.z})

            # 面のローカル座標系を計算（正確な押し出し方向のため）
            local_coord = self._create_face_local_coordinate_system(
                corner_nodes, {"x": center_point.x, "y": center_point.y, "z": center_point.z}
            )

            # 2Dプロファイルを作成（旧版の正確な実装に合わせる）
            profile_points = []
            for node in corner_nodes:
                local_2d = self._transform_to_local_2d(node, local_coord)
                profile_points.append(local_2d)

            ifc_points = [ifc_file.createIfcCartesianPoint(p) for p in profile_points]
            polyline = ifc_file.createIfcPolyLine(ifc_points + [ifc_points[0]])
            profile = ifc_file.createIfcArbitraryClosedProfileDef(
                ProfileType="AREA", OuterCurve=polyline
            )

            # 壁の厚さを取得
            thickness = wall_section.properties.get(
                "thickness", 250.0
            )  # デフォルト250mm

            # 押し出し基準位置を計算（中心点から法線逆方向に厚さ/2オフセット）
            relative_base_location = ifc_file.createIfcCartesianPoint(
                [0.0, 0.0, -thickness / 2.0]
            )
            relative_axis = ifc_file.createIfcDirection([0.0, 0.0, 1.0])  # ローカルZ軸
            relative_ref_dir = ifc_file.createIfcDirection([1.0, 0.0, 0.0])  # ローカルX軸
            solid_placement = ifc_file.createIfcAxis2Placement3D(
                Location=relative_base_location,
                Axis=relative_axis,
                RefDirection=relative_ref_dir,
            )

            # ExtrudedAreaSolidを作成（押し出し方向はローカルZ軸）
            extrusion_vector = ifc_file.createIfcDirection([0.0, 0.0, 1.0])
            solid = ifc_file.createIfcExtrudedAreaSolid(
                SweptArea=profile,
                Position=solid_placement,
                ExtrudedDirection=extrusion_vector,
                Depth=thickness,
            )

            # 開口部処理（旧版の実装を統合）
            if openings:
                self.logger.info(f"壁に{len(openings)}個の開口部を処理します")

            return solid, local_coord

        except Exception as e:
            self.logger.error(f"壁ジオメトリ作成エラー: {e}")
            return None, None

    def _create_placement(self, reference_point: Point3D, local_coord: dict = None):
        """配置を作成（面の法線方向を考慮）"""
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

            # 面の法線方向を考慮した配置
            if local_coord:
                # 面の法線と参照方向を使用した正確な配置
                axis_direction = ifc_file.createIfcDirection(local_coord["z_axis"])
                ref_direction = ifc_file.createIfcDirection(local_coord["x_axis"])
                
                placement = ifc_file.createIfcAxis2Placement3D(
                    Location=location,
                    Axis=axis_direction,
                    RefDirection=ref_direction,
                )
            else:
                # フォールバック: 簡易的な配置（回転なし）
                placement = ifc_file.createIfcAxis2Placement3D(
                    Location=location,
                    Axis=None,  # デフォルトZ軸
                    RefDirection=None,  # デフォルトX軸
                )

            # 適切な親配置を設定（旧版の実装に合わせる）
            parent_placement = None
            if hasattr(self.project_builder, 'current_story') and self.project_builder.current_story:
                # 現在のストーリーの配置を親として使用
                story = self.project_builder.current_story
                if hasattr(story, 'ObjectPlacement') and story.ObjectPlacement:
                    parent_placement = story.ObjectPlacement
            
            return ifc_file.createIfcLocalPlacement(
                PlacementRelTo=parent_placement, RelativePlacement=placement
            )

        except Exception as e:
            self.logger.error(f"配置作成エラー: {e}")
            return None

    def _create_wall_object(
        self, placement, shape, wall_name: str, wall_tag: str, stb_guid: Optional[str]
    ):
        """壁オブジェクトを作成"""
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

            # IFC壁オブジェクトを作成
            wall = ifc_file.createIfcWall(
                GlobalId=element_guid,
                OwnerHistory=self.project_builder.owner_history,
                Name=wall_name,
                Description=None,
                ObjectType=None,
                ObjectPlacement=placement,
                Representation=product_shape,
                Tag=wall_tag,
                PredefinedType="STANDARD",  # 標準壁タイプに設定
            )

            # 壁作成完了をデバッグログに記録
            logger.debug(f"壁を作成しました: 名前={wall_name}, GUID={element_guid}")
            return wall

        except Exception as e:
            self.logger.error(f"壁オブジェクト作成エラー: {e}")
            return None

    def _set_wall_properties(
        self,
        wall,
        corner_points: List[Point3D],
        wall_section: StructuralSection,
        openings: List[Dict],
    ):
        """壁プロパティを設定"""
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

    def create_walls(self, wall_definitions: list) -> list:
        """複数の壁を作成"""
        return self.create_elements(wall_definitions)

    def _create_face_local_coordinate_system(
        self, ordered_nodes: list, center_point: dict = None
    ) -> dict:
        """面のローカル座標系（正規直交基底）を作成"""
        if len(ordered_nodes) < 3:
            raise ValueError("ローカル座標系の作成には最低3つの節点が必要です")

        # 原点は指定されたcenter_pointを使用、なければ重心を計算
        if center_point:
            origin = [center_point["x"], center_point["y"], center_point["z"]]
        else:
            # 全節点の重心を原点として使用
            origin = [
                sum(n["x"] for n in ordered_nodes) / len(ordered_nodes),
                sum(n["y"] for n in ordered_nodes) / len(ordered_nodes),
                sum(n["z"] for n in ordered_nodes) / len(ordered_nodes),
            ]

        # 1. Z軸: 面の法線 (Newellのアルゴリズムで計算)
        z_axis = self._calculate_face_normal(ordered_nodes)

        # 2. Y軸: Z軸と直交するY軸を計算
        # 最初の2節点から仮のX軸を決定
        p0 = ordered_nodes[0]
        p1 = ordered_nodes[1]
        temp_x = [p1["x"] - p0["x"], p1["y"] - p0["y"], p1["z"] - p0["z"]]

        # Y = Z x temp_X
        y_axis = [
            z_axis[1] * temp_x[2] - z_axis[2] * temp_x[1],
            z_axis[2] * temp_x[0] - z_axis[0] * temp_x[2],
            z_axis[0] * temp_x[1] - z_axis[1] * temp_x[0],
        ]
        y_len = math.sqrt(sum(y * y for y in y_axis))

        # 仮X軸がZ軸と平行だった場合のフォールバック
        if y_len < 1e-9:
            self.logger.debug(f"Y軸計算でフォールバック処理を実行（y_len={y_len:.2e}）")
            # 仮のベクトルとしてグローバルX軸を使用
            temp_up = [1.0, 0.0, 0.0]
            # Z軸がグローバルX軸と平行な場合はグローバルY軸を使用
            if abs(abs(sum(t * z for t, z in zip(temp_up, z_axis))) - 1.0) < 1e-9:
                temp_up = [0.0, 1.0, 0.0]
                self.logger.debug("グローバルY軸をフォールバック参照として使用")

            # Y = Z x temp_up
            y_axis = [
                z_axis[1] * temp_up[2] - z_axis[2] * temp_up[1],
                z_axis[2] * temp_up[0] - z_axis[0] * temp_up[2],
                z_axis[0] * temp_up[1] - z_axis[1] * temp_up[0],
            ]
            y_len = math.sqrt(sum(y * y for y in y_axis))
            
            if y_len < 1e-9:
                self.logger.warning("フォールバック処理でもY軸計算に失敗。デフォルト座標系を使用")
                return {"origin": origin, "x_axis": [1.0, 0.0, 0.0], "y_axis": [0.0, 1.0, 0.0], "z_axis": [0.0, 0.0, 1.0]}

        y_axis = [y / y_len for y in y_axis]

        # 3. X軸: Y軸とZ軸から、直交するX軸を再計算 (X = Y x Z)
        x_axis = [
            y_axis[1] * z_axis[2] - y_axis[2] * z_axis[1],
            y_axis[2] * z_axis[0] - y_axis[0] * z_axis[2],
            y_axis[0] * z_axis[1] - y_axis[1] * z_axis[0],
        ]

        return {"origin": origin, "x_axis": x_axis, "y_axis": y_axis, "z_axis": z_axis}

    def _calculate_face_normal(self, nodes: list) -> list:
        """面の法線ベクトルを計算（Newellのアルゴリズムを使用）"""
        if len(nodes) < 3:
            return [0.0, 0.0, 1.0]

        normal = [0.0, 0.0, 0.0]
        num_nodes = len(nodes)

        for i in range(num_nodes):
            p1 = nodes[i]
            p2 = nodes[(i + 1) % num_nodes]

            normal[0] += (p1["y"] - p2["y"]) * (p1["z"] + p2["z"])
            normal[1] += (p1["z"] - p2["z"]) * (p1["x"] + p2["x"])
            normal[2] += (p1["x"] - p2["x"]) * (p1["y"] + p2["y"])

        length = math.sqrt(sum(n * n for n in normal))
        if length > 1e-9:
            normal = [n / length for n in normal]
        else:
            self.logger.warning(
                f"法線ベクトルの計算に失敗しました（長さ={length:.2e}）。デフォルト値Z軸を使用します。"
            )
            return [0.0, 0.0, 1.0]

        return normal

    def _transform_to_local_2d(self, node: dict, coord_system: dict) -> tuple:
        """3D点をローカル座標系の2D座標に変換"""
        # 原点からの相対ベクトル
        vec = [
            node["x"] - coord_system["origin"][0],
            node["y"] - coord_system["origin"][1],
            node["z"] - coord_system["origin"][2],
        ]

        # ローカルX, Y座標を計算
        local_x = sum(v * x for v, x in zip(vec, coord_system["x_axis"]))
        local_y = sum(v * y for v, y in zip(vec, coord_system["y_axis"]))

        return (local_x, local_y)

    def _create_wall_openings(
        self,
        wall,
        openings: List[Dict],
        wall_section: StructuralSection,
        local_coord: dict,
    ):
        """壁の開口要素を作成（STBローカル座標系に対応）

        Args:
            wall: IFC壁オブジェクト
            openings: 開口情報のリスト
            wall_section: 壁の断面情報
            local_coord: 壁のローカル座標系
        """
        if not self.project_builder or not self.project_builder.file:
            return
        
        ifc_file = self.project_builder.file

        for opening_data in openings:
            try:
                # 開口の位置とサイズを取得
                dimensions = opening_data.get("dimensions", {})
                relative_position = opening_data.get("relative_position", {})
                opening_id = opening_data.get("id", "Unknown")

                # 開口のサイズ（STBから取得、mm単位）
                width = float(dimensions.get("width", 1000))  # mm
                height = float(dimensions.get("height", 2000))  # mm

                # 壁の厚さを取得
                wall_thickness = wall_section.properties.get("thickness", 250.0)

                # 開口の形状を作成（矩形）
                opening_profile = ifc_file.createIfcRectangleProfileDef(
                    ProfileType="AREA",
                    ProfileName=f"Opening_{opening_id}",
                    XDim=width,
                    YDim=height,
                )

                # STBの相対位置を取得（壁の最初の節点を基準とした座標）
                # position_X: 壁の長手方向のオフセット
                # position_Y: 壁の高さ方向（Z軸）のオフセット
                rel_x = float(relative_position.get("x", 0))  # 長手方向オフセット
                rel_z = float(relative_position.get("y", 0))  # 高さ方向オフセット

                # 壁の寸法を取得
                wall_length = wall_section.properties.get("length", 6000.0)  # 壁の長さ
                wall_height = wall_section.properties.get("height", 4500.0)  # 壁の高さ

                # STB座標からIFC中心基準座標への変換
                # position_X, position_Yは左下角からのオフセット
                # 壁の中心を基準とした座標に変換
                center_offset_x = rel_x - wall_length / 2.0
                center_offset_z = rel_z - wall_height / 2.0

                # 開口の中心位置を計算（開口プロファイルの中心として配置）
                # 開口の左下角位置に開口サイズの半分を加算して中心位置に調整
                local_x = center_offset_x + width / 2.0
                # 壁のローカル座標系（X:長手, Y:高さ, Z:厚さ）に合わせて修正
                local_y = center_offset_z + height / 2.0  # Yが高さ方向
                local_z = 0.0  # Zが厚さ方向の中心

                # 開口の配置位置（壁のローカル座標系）
                opening_location = ifc_file.createIfcCartesianPoint(
                    [local_x, local_y, local_z]
                )

                # 開口の配置方向（壁のローカル座標系に合わせる）
                # 開口の押し出し方向は壁の厚さ方向（壁のローカルZ軸）
                opening_axis = ifc_file.createIfcDirection(
                    [0.0, 0.0, 1.0]
                )  # Z軸（厚さ方向）
                opening_ref = ifc_file.createIfcDirection(
                    [1.0, 0.0, 0.0]
                )  # X軸（長手方向）

                opening_placement_3d = ifc_file.createIfcAxis2Placement3D(
                    Location=opening_location,
                    Axis=opening_axis,
                    RefDirection=opening_ref,
                )

                # 壁に対する相対配置として設定
                opening_local_placement = ifc_file.createIfcLocalPlacement(
                    PlacementRelTo=wall.ObjectPlacement,  # 壁の配置を基準とする
                    RelativePlacement=opening_placement_3d,
                )

                # 押し出し方向（開口ジオメトリのローカルZ軸方向）
                extrusion_direction = ifc_file.createIfcDirection([0.0, 0.0, 1.0])

                # 壁を確実に貫通させるため、押し出し開始位置をオフセットし、深さを調整
                epsilon = 1.0  # 1mmのクリアランス

                # 開口の押し出しソリッドの配置
                # 壁の厚さの中心から前後にepsilonずつオフセット
                solid_placement = ifc_file.createIfcAxis2Placement3D(
                    Location=ifc_file.createIfcCartesianPoint(
                        [
                            0.0,  # X軸方向のオフセットなし
                            0.0,  # Y軸方向のオフセットなし
                            -wall_thickness / 2.0 - epsilon,  # Z軸方向にオフセット
                        ]
                    )
                )

                # 開口の3Dジオメトリ（押し出しソリッド）
                opening_solid = ifc_file.createIfcExtrudedAreaSolid(
                    SweptArea=opening_profile,
                    Position=solid_placement,
                    ExtrudedDirection=extrusion_direction,
                    Depth=wall_thickness + (2 * epsilon),  # 壁厚より長くして確実に貫通
                )

                # 形状表現
                opening_shape_rep = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=self.project_builder.model_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="SweptSolid",
                    Items=[opening_solid],
                )

                opening_product_shape = ifc_file.createIfcProductDefinitionShape(
                    Representations=[opening_shape_rep]
                )

                # GUIDを生成
                from common.guid_utils import create_ifc_guid
                opening_guid = create_ifc_guid()

                # 開口要素を作成
                opening_element = ifc_file.createIfcOpeningElement(
                    GlobalId=opening_guid,
                    OwnerHistory=self.project_builder.owner_history,
                    Name=f"Opening_{opening_id}",
                    Description=f"Wall opening from STB id={opening_id}",
                    ObjectPlacement=opening_local_placement,
                    Representation=opening_product_shape,
                )

                # 壁と開口の関係を作成（IfcRelVoidsElement）
                rel_voids_guid = create_ifc_guid()
                rel_voids = ifc_file.createIfcRelVoidsElement(
                    GlobalId=rel_voids_guid,
                    OwnerHistory=self.project_builder.owner_history,
                    Name=f"WallVoiding_{opening_id}",
                    Description=f"Voiding relationship for opening {opening_id}",
                    RelatingBuildingElement=wall,
                    RelatedOpeningElement=opening_element,
                )

                self.logger.debug(
                    f"開口 {opening_id} を作成: 幅={width}mm, 高さ={height}mm, "
                    f"STB位置=({rel_x}, {rel_z}), 中心オフセット=({center_offset_x:.1f}, {center_offset_z:.1f}), "
                    f"最終ローカル位置=({local_x:.1f}, {local_y:.1f}, {local_z:.1f})"
                )

            except Exception as e:
                self.logger.error(
                    f"開口 {opening_data.get('id', 'Unknown')} の作成に失敗: {e}"
                )
                import traceback
                traceback.print_exc()
                continue
