# footing_extractor.py
from typing import Dict, List, Optional
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger

logger = get_logger(__name__)


class FootingExtractor(BaseExtractor):
    """ST-Bridge フーチングメンバー情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_footings(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        """フーチング情報を抽出してIFC用の辞書形式で返す

        Args:
            nodes_data: ノード情報の辞書（node_id -> node_info）
            sections_data: 断面情報の辞書（section_id -> section_info）

        Returns:
            フーチング定義リスト（各要素は辞書形式）
        """
        config = STBExtractionConfigs.get_footing_config()
        return self.extract_elements(nodes_data, sections_data, config)

    def _extract_single_element(
        self,
        footing_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ) -> Optional[Dict]:
        """単一要素の抽出処理（BaseExtractorから継承）"""
        return self._extract_single_footing(
            footing_elem, nodes_data, sections_data
        )

    def _extract_single_footing(
        self,
        footing_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
    ) -> Optional[Dict]:
        """単一のフーチング要素を処理"""
        footing_id = footing_elem.get("id")
        footing_guid = footing_elem.get("guid")
        footing_name = footing_elem.get("name", f"Footing_{footing_id}")

        # ノード情報の取得
        id_node = footing_elem.get("id_node")
        if not id_node or id_node not in nodes_data:
            logger.warning(
                "フーチング %s: ノードID %s が見つかりません",
                footing_id,
                id_node,
            )
            return None

        node_info = nodes_data[id_node]

        # 断面情報の取得
        id_section = footing_elem.get("id_section")
        if not id_section or id_section not in sections_data:
            logger.warning(
                "フーチング %s: 断面ID %s が見つかりません",
                footing_id,
                id_section,
            )
            return None

        section_info = sections_data[id_section]

        # オフセット情報（オプション）
        offset_x = float(footing_elem.get("offset_X", 0))
        offset_y = float(footing_elem.get("offset_Y", 0))

        # レベル情報
        level_bottom = float(footing_elem.get("level_bottom", 0))

        # 回転情報（オプション）
        rotate = float(footing_elem.get("rotate", 0))

        # 座標計算
        x = node_info["x"] + offset_x
        y = node_info["y"] + offset_y
        z = node_info["z"] + level_bottom  # level_bottomを足してZ座標を計算

        # フーチング定義辞書の構築
        footing_def = {
            "id": footing_id,
            "guid": footing_guid,
            "name": footing_name,
            "tag": f"FT_{footing_id}",
            "type": "Footing",
            # 位置情報
            "bottom_point": {"x": x, "y": y, "z": z},
            # ノード情報
            "id_node": id_node,
            "node_id": id_node,  # Story関連付け用
            "node_info": node_info,
            # 断面情報
            "section": self._process_footing_section(section_info),
            "id_section": id_section,
            "section_info": section_info,
            # 寸法情報
            "thickness": self._extract_thickness_from_section(section_info),
            # 変換用の追加情報
            "offset_x": offset_x,
            "offset_y": offset_y,
            "level_bottom": level_bottom,
            "rotate": rotate,
            "stb_original_id": footing_id,
            "stb_guid": footing_guid,
            "stb_section_name": section_info.get("stb_name", "Unknown"),
        }

        # 階層情報を設定（STB上に階の設定が無い場合はGLに紐づける）
        floor_attribute = footing_elem.get("floor")
        if floor_attribute:
            footing_def["floor"] = floor_attribute
            logger.debug(
                "フーチング ID %s に階層情報を設定: floor='%s'", footing_id, floor_attribute
            )
        else:
            # STB上に階の設定が無い場合はGLに紐づける
            footing_def["floor"] = "GL"
            logger.debug(
                "フーチング ID %s に階層情報がないため、GLに設定しました", footing_id
            )

        logger.debug("フーチング %s を抽出しました: %s", footing_id, footing_name)
        return footing_def

    def _process_footing_section(self, section_info: Dict) -> Dict:
        """フーチング断面情報をIFC形式に変換"""
        # デフォルトは矩形断面
        section = {
            "section_type": "RECTANGLE",
            "width_x": section_info.get("width_X", 1000.0),
            "width_y": section_info.get("width_Y", 1000.0),
        }

        # STB断面タイプに応じて処理を分岐（将来の拡張用）
        section_type = section_info.get("section_type", "RECTANGLE")
        if section_type == "RECTANGLE":
            # 既にデフォルトで設定済み
            pass
        elif section_type == "CIRCLE":
            # 円形フーチング（将来対応）
            radius = section_info.get("radius", 500.0)
            section = {
                "section_type": "CIRCLE",
                "radius": radius,
            }

        return section

    def _extract_thickness_from_section(self, section_info: Dict) -> float:
        """断面情報から厚さを抽出"""
        # depth または thickness を厚さとして使用
        thickness = section_info.get("depth", section_info.get("thickness", 600.0))
        return float(thickness)
