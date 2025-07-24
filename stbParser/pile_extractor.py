# pile_extractor.py
"""ST-Bridge 杭メンバー情報抽出クラス"""

from typing import Dict, List
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger

logger = get_logger(__name__)


class PileExtractor(BaseExtractor):
    """ST-Bridge 杭メンバーの抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_piles(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        """杭メンバー情報を抽出しIFC用辞書リストに変換"""
        config = STBExtractionConfigs.get_pile_config()
        return self.extract_elements(nodes_data, sections_data, config)

    def _extract_single_element(
        self,
        pile_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ):
        """単一要素の抽出処理（BaseExtractorから継承）"""
        return self._extract_single_pile(pile_elem, nodes_data, sections_data)

    def _extract_single_pile(
        self, pile_elem, nodes_data: Dict, sections_data: Dict
    ) -> Dict:
        pile_id = pile_elem.get("id")
        pile_name = pile_elem.get("name", f"Pile_{pile_id}")
        node_id = pile_elem.get("id_node")
        section_id = pile_elem.get("id_section")
        kind_structure = pile_elem.get("kind_structure")

        # 階層情報の取得（他の要素と同様）
        floor_attribute = pile_elem.get("floor")

        if node_id not in nodes_data or section_id not in sections_data:
            logger.warning("杭 ID %s のノードまたは断面が見つかりません", pile_id)
            return None

        node = nodes_data[node_id]
        offset_x = float(pile_elem.get("offset_X", 0))
        offset_y = float(pile_elem.get("offset_Y", 0))
        level_top = float(pile_elem.get("level_top", node["z"]))
        length_all = pile_elem.get("length_all")
        if length_all:
            try:
                bottom_z = level_top - float(length_all)
            except ValueError:
                bottom_z = level_top
        else:
            bottom_z = level_top

        start_point = {
            "x": node["x"] + offset_x,
            "y": node["y"] + offset_y,
            "z": level_top,
        }
        end_point = {
            "x": node["x"] + offset_x,
            "y": node["y"] + offset_y,
            "z": bottom_z,
        }
        section_info = sections_data[section_id]

        pile_def = {
            "name": pile_name,
            "tag": f"STB_P_{pile_id}",
            "top_point": start_point,
            "bottom_point": end_point,
            "node_id": node_id,  # Story関連付け用（互換）
            "bottom_node_id": node_id,  # Story関連付け用（杭は下端ノードで階層判定）
            "section": section_info,
            "stb_original_id": pile_id,
            "stb_guid": pile_elem.get("guid"),
            "stb_section_name": section_info.get("stb_name", "Unknown"),
            "stb_structure_type": kind_structure,
        }

        # 階層情報を明示的に設定（他の要素と同様）
        if floor_attribute:
            pile_def["floor"] = floor_attribute
            logger.debug(
                "杭 ID %s に階層情報を設定: floor='%s'", pile_id, floor_attribute
            )
        else:
            # STB上に階の設定が無い場合はGLに紐づける
            pile_def["floor"] = "GL"
            logger.debug(
                "杭 ID %s に階層情報がないため、GLに設定しました", pile_id
            )

        return pile_def
