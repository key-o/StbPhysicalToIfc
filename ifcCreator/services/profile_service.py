"""Profile Service

統一プロファイル作成サービス
複数ファイルに分散していたプロファイル作成ロジックを統一し、
重複を削除してシンプルなインターフェースを提供する責務分離アーキテクチャ
"""

from typing import Optional, Dict, Any, Union
import logging
from dataclasses import dataclass

# v2.2.0: 統合アーキテクチャ - 簡素化されたプロファイル作成

logger = logging.getLogger(__name__)


class ProfileService:
    """プロファイル作成の統一サービス

    v2.2.0: 簡素化された統一実装
    """

    def __init__(self, ifc_file=None):
        """ProfileServiceの初期化

        Args:
            ifc_file: IFCファイルオブジェクト（オプション）
        """
        self.file = ifc_file
        self._cache: Dict[str, Any] = {}

    def create_profile(self, section, element_type: str):
        """統一プロファイル作成インターフェース

        Args:
            section: セクション定義
            element_type: 要素タイプ (beam, column, slab, wall, etc.)

        Returns:
            作成されたプロファイル（プレースホルダー）
        """
        cache_key = self._generate_cache_key(section, element_type)
        if cache_key in self._cache:
            logger.debug(f"Profile cache hit: {cache_key}")
            return self._cache[cache_key]

        # v2.2.0: 簡素化されたプロファイル作成
        profile = self._create_simple_profile(section, element_type)

        self._cache[cache_key] = profile
        logger.debug(f"Profile created and cached: {cache_key}")
        return profile

    def _generate_cache_key(self, section, element_type: str) -> str:
        """キャッシュキーの生成"""
        # セクションの主要属性からキーを生成
        key_parts = [element_type]

        if hasattr(section, "name"):
            key_parts.append(f"name:{section.name}")
        if hasattr(section, "width"):
            key_parts.append(f"w:{section.width}")
        if hasattr(section, "height"):
            key_parts.append(f"h:{section.height}")
        if hasattr(section, "section_type"):
            key_parts.append(f"type:{section.section_type}")

        return "_".join(key_parts)

    def _create_simple_profile(self, section, element_type: str):
        """実際のIFCプロファイル作成

        旧版のProfileFactoryBaseロジックを統合
        """
        if not self.file:
            # プレースホルダー実装（IFCファイルがない場合）
            return {
                "type": element_type,
                "section_type": getattr(section, "section_type", "Unknown"),
                "name": getattr(section, "name", "DefaultProfile"),
                "dimensions": self._extract_dimensions(section),
            }

        # 実際のIFCプロファイル作成（旧版ロジック統合）
        section_type = getattr(section, "section_type", "RECTANGLE")

        if section_type == "RECTANGLE":
            return self._create_rectangle_profile(section, element_type)
        elif section_type == "CIRCLE":
            return self._create_circle_profile(section, element_type)
        elif section_type == "H":
            return self._create_h_profile(section, element_type)
        elif section_type == "BOX":
            return self._create_box_profile(section, element_type)
        elif section_type in ("C", "CHANNEL"):
            return self._create_channel_profile(section, element_type)
        elif section_type == "PIPE":
            return self._create_pipe_profile(section, element_type)
        elif section_type == "L":
            return self._create_l_profile(section, element_type)
        else:
            logger.warning(f"Unsupported section type: {section_type}, using rectangle")
            return self._create_rectangle_profile(section, element_type)

    def _extract_dimensions(self, section) -> Dict[str, Any]:
        """セクションから寸法情報を抽出"""
        dimensions = {}
        dimension_attrs = [
            "width",
            "height",
            "thickness",
            "radius",
            "overall_depth",
            "overall_width",
            "web_thickness",
            "flange_thickness",
            "outer_diameter",
        ]

        for attr in dimension_attrs:
            if hasattr(section, attr):
                dimensions[attr] = getattr(section, attr)

        return dimensions

    def get_profile_factory(self, element_type: str):
        """要素タイプ別プロファイルファクトリを取得

        Args:
            element_type: 要素タイプ

        Returns:
            適切なプロファイルファクトリ（プレースホルダー）
        """
        return self  # v2.2.0: 自身を返すプレースホルダー実装

    def clear_cache(self):
        """プロファイルキャッシュをクリア"""
        self._cache.clear()
        logger.info("Profile cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報を取得"""
        return {"cache_size": len(self._cache), "cache_keys": list(self._cache.keys())}

    # === 旧版から移植したプロファイル作成メソッド ===

    def _create_rectangle_profile(self, section, element_type: str):
        """矩形プロファイル作成（旧版ProfileFactoryBaseから移植）"""
        if not self.file:
            raise ValueError("IFC file is required for profile creation")

        width, height = self._get_rectangle_dimensions(section)

        if None in (width, height):
            raise ValueError(
                "Width and height must be specified for rectangular section"
            )

        y_offset = self._calculate_y_offset(section, height, element_type)
        pos2d = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([0.0, y_offset])
        )

        profile_name = (
            getattr(section, "stb_name", None) or f"RectProfile_{width}x{height}"
        )
        return self.file.createIfcRectangleProfileDef(
            ProfileType="AREA",
            ProfileName=profile_name,
            Position=pos2d,
            XDim=width,
            YDim=height,
        )

    def _create_circle_profile(self, section, element_type: str):
        """円形プロファイル作成（旧版ProfileFactoryBaseから移植）"""
        if not self.file:
            raise ValueError("IFC file is required for profile creation")

        radius = getattr(section, "radius", None)
        if radius is None:
            raise ValueError("Radius must be specified for circular section")

        y_offset = self._calculate_y_offset(section, radius * 2, element_type)
        pos2d = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([0.0, y_offset])
        )

        profile_name = getattr(section, "stb_name", None) or f"CircleProfile_R{radius}"
        return self.file.createIfcCircleProfileDef(
            ProfileType="AREA",
            ProfileName=profile_name,
            Position=pos2d,
            Radius=radius,
        )

    def _create_h_profile(self, section, element_type: str):
        """H形プロファイル作成（旧版ProfileFactoryBaseから移植）"""
        required_attrs = [
            getattr(section, "overall_depth", None),
            getattr(section, "overall_width", None),
            getattr(section, "web_thickness", None),
            getattr(section, "flange_thickness", None),
        ]
        if None in required_attrs:
            raise ValueError("H-shape parameters must be specified")

        overall_depth = section.overall_depth
        overall_width = section.overall_width
        web_thickness = section.web_thickness
        flange_thickness = section.flange_thickness

        y_offset = self._calculate_y_offset(section, overall_depth, element_type)
        pos2d = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([0.0, y_offset])
        )

        profile_name = getattr(section, "stb_name", None) or (
            f"HProfile_{overall_depth}x{overall_width}x{web_thickness}x{flange_thickness}"
        )

        return self.file.createIfcIShapeProfileDef(
            ProfileType="AREA",
            ProfileName=profile_name,
            Position=pos2d,
            OverallDepth=overall_depth,
            OverallWidth=overall_width,
            WebThickness=web_thickness,
            FlangeThickness=flange_thickness,
            FilletRadius=getattr(section, "fillet_radius", None),
        )

    def _create_box_profile(self, section, element_type: str):
        """BOXプロファイル作成（旧版ProfileFactoryBaseから移植）"""
        # 実装を簡略化 - 必要に応じて拡張
        width = getattr(section, "outer_width", None) or getattr(section, "width", None)
        height = getattr(section, "outer_height", None) or getattr(
            section, "height", None
        )
        thickness = getattr(section, "wall_thickness", None) or getattr(
            section, "thickness", None
        )

        if None in (width, height, thickness):
            raise ValueError("BOX section parameters must be specified")

        y_offset = self._calculate_y_offset(section, height, element_type)
        pos2d = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([0.0, y_offset])
        )

        profile_name = (
            getattr(section, "stb_name", None)
            or f"BoxProfile_{width}x{height}x{thickness}"
        )

        return self.file.createIfcRectangleHollowProfileDef(
            ProfileType="AREA",
            ProfileName=profile_name,
            Position=pos2d,
            XDim=width,
            YDim=height,
            WallThickness=thickness,
            InnerFilletRadius=getattr(section, "corner_radius", None),
        )

    def _create_channel_profile(self, section, element_type: str):
        """チャンネルプロファイル作成（旧版ProfileFactoryBaseから移植）"""
        # 基本的なチャンネル形状のプレースホルダー実装
        overall_depth = getattr(section, "overall_depth", None) or getattr(
            section, "height", None
        )
        flange_width = getattr(section, "flange_width", None) or getattr(
            section, "width", None
        )
        web_thickness = getattr(section, "web_thickness", None) or getattr(
            section, "thickness", None
        )
        flange_thickness = getattr(section, "flange_thickness", None) or web_thickness

        if None in (overall_depth, flange_width, web_thickness):
            raise ValueError("Channel section parameters must be specified")

        y_offset = self._calculate_y_offset(section, overall_depth, element_type)
        pos2d = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([0.0, y_offset])
        )

        profile_name = (
            getattr(section, "stb_name", None)
            or f"ChannelProfile_{overall_depth}x{flange_width}"
        )

        return self.file.createIfcCShapeProfileDef(
            ProfileType="AREA",
            ProfileName=profile_name,
            Position=pos2d,
            Depth=overall_depth,
            Width=flange_width,
            WallThickness=web_thickness,
            Girth=flange_thickness,
        )

    def _create_pipe_profile(self, section, element_type: str):
        """パイププロファイル作成（旧版ProfileFactoryBaseから移植）"""
        outer_diameter = getattr(section, "outer_diameter", None)
        thickness = getattr(section, "wall_thickness", None) or getattr(
            section, "thickness", None
        )

        if None in (outer_diameter, thickness):
            raise ValueError("Pipe section parameters must be specified")

        radius = outer_diameter / 2
        y_offset = self._calculate_y_offset(section, outer_diameter, element_type)
        pos2d = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([0.0, y_offset])
        )

        profile_name = (
            getattr(section, "stb_name", None)
            or f"PipeProfile_D{outer_diameter}x{thickness}"
        )

        return self.file.createIfcCircleHollowProfileDef(
            ProfileType="AREA",
            ProfileName=profile_name,
            Position=pos2d,
            Radius=radius,
            WallThickness=thickness,
        )

    def _create_l_profile(self, section, element_type: str):
        """L形プロファイル作成（旧版ProfileFactoryBaseから移植）"""
        # 基本的なL形状のプレースホルダー実装
        width = getattr(section, "width", None)
        height = getattr(section, "height", None)
        thickness = getattr(section, "thickness", None)

        if None in (width, height, thickness):
            raise ValueError("L section parameters must be specified")

        y_offset = self._calculate_y_offset(section, height, element_type)
        pos2d = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([0.0, y_offset])
        )

        profile_name = (
            getattr(section, "stb_name", None)
            or f"LProfile_{width}x{height}x{thickness}"
        )

        return self.file.createIfcLShapeProfileDef(
            ProfileType="AREA",
            ProfileName=profile_name,
            Position=pos2d,
            Depth=height,
            Width=width,
            Thickness=thickness,
        )

    def _get_rectangle_dimensions(self, section):
        """矩形寸法取得（梁・柱対応）"""
        # 梁用
        width = getattr(section, "width", None)
        height = getattr(section, "height", None)

        # 柱用
        if width is None:
            width = getattr(section, "width_x", None)
        if height is None:
            height = getattr(section, "width_y", None)

        return width, height

    def _calculate_y_offset(self, section, height, element_type):
        """Y軸オフセット計算（旧版ロジック）"""
        # 梁の場合は通常上端中心、柱の場合は中心
        if element_type.lower() == "beam":
            return -height / 2  # 上端中心配置
        else:
            return 0.0  # 中心配置
