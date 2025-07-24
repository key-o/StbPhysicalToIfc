# common/definition_processor.py
"""
共通の定義処理ユーティリティ
Creator クラスの process_*_definition メソッドの重複を解決
"""

from typing import Dict, Any, Type, Optional
from common.geometry import Point3D


class DefinitionProcessor:
    """要素定義処理の共通ロジック"""

    @staticmethod
    def process_linear_element_definition(
        element_def: Dict[str, Any],
        index: int,
        element_name: str,
        section_class: Type,
        start_point_key: str = "start_point",
        end_point_key: str = "end_point",
        start_section_key: str = "section_start",
        end_section_key: str = "section_end",
        section_key: str = "section",
    ) -> Dict[str, Any]:
        """線形要素（梁、ブレース等）の定義を処理

        Args:
            element_def: 要素定義辞書
            index: インデックス（ログ用）
            element_name: 要素名（例：「梁」「ブレース」）
            section_class: 断面クラス（BeamSection, BraceSection等）
            start_point_key: 開始点のキー名
            end_point_key: 終了点のキー名
            start_section_key: 開始断面のキー名
            end_section_key: 終了断面のキー名
            section_key: 断面のキー名（統一断面の場合）

        Returns:
            処理済み定義辞書

        Raises:
            ValueError: 必要なパラメータが不足している場合
        """
        # ポイント処理
        start_point = DefinitionProcessor._convert_point_dict(
            element_def.get(start_point_key)
        )
        end_point = DefinitionProcessor._convert_point_dict(
            element_def.get(end_point_key)
        )

        # セクション処理
        raw_sec_start = element_def.get(start_section_key) or element_def.get(section_key)
        raw_sec_end = element_def.get(end_section_key) or element_def.get(section_key)

        sec_start = DefinitionProcessor._convert_section_dict(raw_sec_start, section_class)
        sec_end = DefinitionProcessor._convert_section_dict(raw_sec_end, section_class)

        # 必要なパラメータの検証
        if not all([start_point, end_point, sec_start, sec_end]):
            missing_params = []
            if not start_point:
                missing_params.append(start_point_key)
            if not end_point:
                missing_params.append(end_point_key)
            if not sec_start:
                missing_params.append("sec_start")
            if not sec_end:
                missing_params.append("sec_end")
            raise ValueError(
                f"{element_name}{index + 1}: 必要なパラメータが不足: {', '.join(missing_params)}"
            )

        return {
            start_point_key: start_point,
            end_point_key: end_point,
            "sec_start": sec_start,
            "sec_end": sec_end,
            "name": element_def.get("name"),
            "tag": element_def.get("tag"),
            "stb_guid": element_def.get("stb_guid"),
        }

    @staticmethod
    def process_vertical_element_definition(
        element_def: Dict[str, Any],
        index: int,
        element_name: str,
        section_class: Type,
        bottom_point_key: str = "bottom_point",
        top_point_key: str = "top_point",
        bottom_section_key: str = "section_bottom",
        top_section_key: str = "section_top",
        section_key: str = "section",
    ) -> Dict[str, Any]:
        """垂直要素（柱等）の定義を処理

        Args:
            element_def: 要素定義辞書
            index: インデックス（ログ用）
            element_name: 要素名（例：「柱」）
            section_class: 断面クラス（ColumnSection等）
            bottom_point_key: 下端点のキー名
            top_point_key: 上端点のキー名
            bottom_section_key: 下端断面のキー名
            top_section_key: 上端断面のキー名
            section_key: 断面のキー名（統一断面の場合）

        Returns:
            処理済み定義辞書

        Raises:
            ValueError: 必要なパラメータが不足している場合
        """
        # ポイント処理
        bottom_point = DefinitionProcessor._convert_point_dict(
            element_def.get(bottom_point_key)
        )
        top_point = DefinitionProcessor._convert_point_dict(
            element_def.get(top_point_key)
        )

        # セクション処理
        raw_section = element_def.get(section_key)
        raw_sec_bottom = element_def.get(bottom_section_key)
        raw_sec_top = element_def.get(top_section_key)

        # 統一断面または個別断面の処理
        if raw_section and not raw_sec_bottom and not raw_sec_top:
            # 統一断面の場合（通常の柱）
            section = DefinitionProcessor._convert_section_dict(raw_section, section_class)
            sec_bottom = section
            sec_top = section
        else:
            # 個別断面の場合（テーパー柱）
            section = None
            sec_bottom = DefinitionProcessor._convert_section_dict(raw_sec_bottom, section_class) if raw_sec_bottom else None
            sec_top = DefinitionProcessor._convert_section_dict(raw_sec_top, section_class) if raw_sec_top else None

        # 回転角度とisReferenceDirectionを取得
        rotation_radians = element_def.get("rotate_radians", 0.0)
        is_reference_direction = element_def.get("is_reference_direction", False)

        # 必要なパラメータの検証
        missing_params = []
        if not bottom_point:
            missing_params.append(bottom_point_key)
        if not top_point:
            missing_params.append(top_point_key)
        
        # 断面情報の検証：統一断面または個別断面のどちらかが必要
        if not (section or (sec_bottom and sec_top)):
            if not section:
                missing_params.append(section_key)
            if not sec_bottom:
                missing_params.append("sec_bottom")
            if not sec_top:
                missing_params.append("sec_top")
        
        if missing_params:
            raise ValueError(
                f"{element_name}{index + 1}: 必要なパラメータが不足: {', '.join(missing_params)}"
            )
        
        return {
            bottom_point_key: bottom_point,
            top_point_key: top_point,
            "sec_bottom": sec_bottom,
            "sec_top": sec_top,
            "section": section,  # 統一断面用
            "name": element_def.get("name"),
            "tag": element_def.get("tag"),
            "stb_guid": element_def.get("stb_guid"),
            "rotation_radians": rotation_radians,
            "is_reference_direction": is_reference_direction,
        }

    @staticmethod
    def _convert_point_dict(point_dict: Any) -> Optional[Point3D]:
        """辞書からPoint3Dオブジェクトに変換"""
        if point_dict and isinstance(point_dict, dict):
            return Point3D(point_dict["x"], point_dict["y"], point_dict["z"])
        return point_dict

    @staticmethod
    def _convert_section_dict(raw_section: Any, section_class: Type) -> Any:
        """辞書から断面オブジェクトに変換"""
        if isinstance(raw_section, dict):
            return section_class.from_dict(raw_section)
        return raw_section