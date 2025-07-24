# brace_extractor.py
from typing import Dict, List, Optional, Tuple
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger

logger = get_logger(__name__)


class BraceExtractor(BaseExtractor):
    """Extracts brace member information from ST-Bridge XML."""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_braces(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        config = STBExtractionConfigs.get_brace_config()
        return self.extract_elements(nodes_data, sections_data, config)

    def _extract_single_element(
        self,
        brace_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str,
    ) -> Optional[Dict]:
        """単一要素の抽出処理（BaseExtractorから継承）"""
        brace_def = self._extract_single_brace(
            brace_elem, nodes_data, sections_data, node_story_map
        )
        if brace_def:
            logger.info(
                "StbBrace ID %s の断面 '%s' を解析しました",
                brace_def["stb_original_id"],
                brace_def["stb_section_name"],
            )
        return brace_def

    def _extract_single_brace(
        self,
        brace_elem,
        nodes_data: Dict,
        sections_data: Dict,
        node_story_map: Dict,
    ) -> Optional[Dict]:
        brace_id = brace_elem.get("id")
        brace_name = brace_elem.get("name", f"Brace_{brace_id}")
        id_node_start = brace_elem.get("id_node_start")
        id_node_end = brace_elem.get("id_node_end")
        id_section = brace_elem.get("id_section")
        kind_structure = brace_elem.get("kind_structure")
        feature_brace = brace_elem.get("feature_brace")  # ブレース特性を追加

        if not self._validate_brace_data(
            brace_id, id_node_start, id_node_end, id_section, nodes_data, sections_data
        ):
            return None

        start_node, end_node = self._apply_node_offsets(brace_elem, nodes_data)
        section_info = sections_data[id_section]

        brace_def = {
            "name": brace_name,
            "tag": f"STB_BR_{brace_id}",
            "start_point": start_node,
            "end_point": end_node,
            "start_node_id": id_node_start,  # Story関連付け用
            "end_node_id": id_node_end,  # Story関連付け用
            "section": section_info,
            "stb_original_id": brace_id,
            "stb_guid": brace_elem.get("guid"),
            "stb_section_name": section_info.get("stb_name", "Unknown"),
            "stb_structure_type": kind_structure,
            "feature_brace": feature_brace,  # ブレース特性を追加
        }  # 階層情報を設定（開始ノードのみを使用）
        floor_attribute = brace_elem.get("floor")
        if floor_attribute:
            brace_def["floor"] = floor_attribute
        elif node_story_map is not None:
            # 開始ノードから階層を特定
            story_name = node_story_map.get(id_node_start)  # 開始ノードの階層を取得
            if story_name:
                brace_def["floor"] = story_name

        return brace_def

    def _apply_node_offsets(self, brace_elem, nodes_data: Dict) -> Tuple[Dict, Dict]:
        id_node_start = brace_elem.get("id_node_start")
        id_node_end = brace_elem.get("id_node_end")
        offset_start_x = float(brace_elem.get("offset_start_X", 0))
        offset_start_y = float(brace_elem.get("offset_start_Y", 0))
        offset_start_z = float(brace_elem.get("offset_start_Z", 0))
        offset_end_x = float(brace_elem.get("offset_end_X", 0))
        offset_end_y = float(brace_elem.get("offset_end_Y", 0))
        offset_end_z = float(brace_elem.get("offset_end_Z", 0))

        original_start = nodes_data[id_node_start]
        original_end = nodes_data[id_node_end]

        corrected_start = {
            "x": original_start["x"] + offset_start_x,
            "y": original_start["y"] + offset_start_y,
            "z": original_start["z"] + offset_start_z,
        }
        corrected_end = {
            "x": original_end["x"] + offset_end_x,
            "y": original_end["y"] + offset_end_y,
            "z": original_end["z"] + offset_end_z,
        }
        return corrected_start, corrected_end

    def _validate_brace_data(
        self,
        brace_id: str,
        id_node_start: str,
        id_node_end: str,
        id_section: str,
        nodes_data: Dict,
        sections_data: Dict,
    ) -> bool:
        missing_parts = []
        if id_node_start not in nodes_data:
            missing_parts.append(f"start node {id_node_start}")
        if id_node_end not in nodes_data:
            missing_parts.append(f"end node {id_node_end}")
        if id_section not in sections_data:
            missing_parts.append(f"section {id_section}")

        if missing_parts:
            logger.warning(
                "Brace ID %s has missing data: %s",
                brace_id,
                ", ".join(missing_parts),
            )
            return False
        return True
