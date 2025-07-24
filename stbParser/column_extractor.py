# column_extractor.py
import math
from typing import Dict, List, Tuple
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger


logger = get_logger(__name__)


class ColumnExtractor(BaseExtractor):
    """ST-Bridge柱メンバー情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_columns(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        """ST-Bridgeから柱メンバー情報を抽出してIFC用辞書リストに変換

        Args:
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書

        Returns:
            柱定義リスト（各要素は辞書形式）
        """
        config = STBExtractionConfigs.get_column_config()
        return self.extract_elements(nodes_data, sections_data, config)



    def _extract_single_element(
        self,
        column_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ):
        """単一要素の抽出処理（BaseExtractorから継承）"""
        return self._extract_single_column(
            column_elem, nodes_data, sections_data, node_story_map, element_type
        )

    def _extract_single_column(
        self,
        column_elem,
        nodes_data: Dict,
        sections_data: Dict,
        node_story_map: Dict,
        column_type: str = "StbColumn",
    ) -> Dict | None:
        """単一の柱要素からIFC用辞書を作成

        Args:
            column_elem: 柱のXML要素（StbColumnまたはStbPost）
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書
            node_story_map: ノードIDと階層名のマッピング辞書
            column_type: 柱要素のタイプ（"StbColumn"または"StbPost"）

        Returns:
            柱定義辞書、または抽出失敗時None
        """
        column_id = column_elem.get("id")
        column_guid = column_elem.get("guid")
        column_name = column_elem.get("name", f"{column_type}_{column_id}")

        # ノード属性の取得（StbColumnとStbPostで属性名が異なる）
        if column_type == "StbPost":
            id_node_bottom = column_elem.get("id_node_bottom")
            id_node_top = column_elem.get("id_node_top")
        else:  # StbColumn
            id_node_bottom = column_elem.get("id_node_bottom")
            id_node_top = column_elem.get("id_node_top")

        id_section = column_elem.get("id_section")
        kind_structure = column_elem.get("kind_structure")  # RC, S, SRCなど

        # 回転角度を取得（デフォルトは0）
        rotate_degrees = float(column_elem.get("rotate", 0))
        rotate_radians = self._degrees_to_radians(rotate_degrees)

        # isReferenceDirection属性を取得（デフォルトはfalse）
        # これは断面がセクション定義から取得されるため、断面情報から取得する必要がある

        logger.debug(
            "%s ID %s を処理: bottom=%s, top=%s, section=%s",
            column_type,
            column_id,
            id_node_bottom,
            id_node_top,
            id_section,
        )

        # 必要なデータの存在確認
        if not self._validate_column_data(
            column_id,
            id_node_bottom,
            id_node_top,
            id_section,
            nodes_data,
            sections_data,
        ):
            return None  # オフセットを適用した座標を取得
        bottom_node, top_node = self._apply_node_offsets(column_elem, nodes_data)
        section_info = sections_data[id_section]

        # 断面のisReferenceDirectionを取得
        is_reference_direction = section_info.get("is_reference_direction", False)

        column_def = {
            "name": column_name,
            "tag": f"STB_C_{column_id}",  # IFC Tagとして使用
            "bottom_point": bottom_node,  # {'x': ..., 'y': ..., 'z': ...}
            "top_point": top_node,  # {'x': ..., 'y': ..., 'z': ...}
            "bottom_node_id": id_node_bottom,  # Story関連付け用
            "top_node_id": id_node_top,  # Story関連付け用
            "stb_original_id": column_id,  # 元のST-Bridge IDを保持
            "stb_guid": column_guid,
            "stb_section_name": section_info.get("stb_name", "Unknown"),
            "stb_structure_type": kind_structure,  # RC, S, SRC等
            "rotate_degrees": rotate_degrees,  # 回転角度（度）
            "rotate_radians": rotate_radians,  # 回転角度（ラジアン）
            "is_reference_direction": is_reference_direction,  # H型配置判定
        }

        # 階層情報を設定（下部ノードのみを使用）
        floor_attribute = column_elem.get("floor")
        if floor_attribute:
            column_def["floor"] = floor_attribute
            logger.debug(
                "柱 ID %s に階層情報を設定: floor='%s'", column_id, floor_attribute
            )
        elif node_story_map is not None:
            # 下部ノードから階層を特定
            story_name = node_story_map.get(id_node_bottom)  # 下部ノードの階層を取得
            if story_name:
                column_def["floor"] = story_name
                logger.debug(
                    "柱 ID %s にノードから特定した階層情報を設定: floor='%s'",
                    column_id,
                    story_name,
                )
            else:
                logger.warning(
                    "柱 ID %s の階層情報を特定できませんでした: node_bottom=%s",
                    column_id,
                    id_node_bottom,
                )

        if "start_section" in section_info and "end_section" in section_info:
            column_def["sec_bottom"] = section_info["start_section"]
            column_def["sec_top"] = section_info["end_section"]
        else:
            column_def["section"] = section_info

        logger.debug(
            "Column %s rotation: %s° (%s rad)",
            column_id,
            rotate_degrees,
            rotate_radians,
        )
        return column_def

    def _apply_node_offsets(self, column_elem, nodes_data: Dict) -> Tuple[Dict, Dict]:
        """ノード座標にオフセットを適用して補正された座標を返す

        Args:
            column_elem: 柱のXML要素
            nodes_data: ノード情報辞書

        Returns:
            補正された下端ノードと上端ノードの座標
        """
        from common.extractor_utils import NodeOffsetUtils

        return NodeOffsetUtils.apply_vertical_node_offsets(column_elem, nodes_data)

    def _degrees_to_radians(self, degrees: float) -> float:
        """度をラジアンに変換

        Args:
            degrees: 角度（度）

        Returns:
            角度（ラジアン）
        """
        from common.extractor_utils import AngleUtils

        return AngleUtils.degrees_to_radians(degrees)

    def _validate_column_data(
        self,
        column_id: str,
        id_node_bottom: str,
        id_node_top: str,
        id_section: str,
        nodes_data: Dict,
        sections_data: Dict,
    ) -> bool:
        """柱データの妥当性を確認

        Args:
            column_id: 柱ID
            id_node_bottom: 下端ノードID
            id_node_top: 上端ノードID
            id_section: 断面ID
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書

        Returns:
            データが揃っている場合True、不足している場合False
        """
        from common.extractor_utils import ElementValidator

        return ElementValidator.validate_element_data(
            column_id,
            "Column",
            [id_node_bottom, id_node_top],
            [id_section],
            nodes_data,
            sections_data,
        )
