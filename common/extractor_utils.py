# common/extractor_utils.py
"""
抽出クラス共通ユーティリティ
ExtractorクラスのNode Offset処理とValidation処理の重複を解決
"""

import math
from typing import Dict, List, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class NodeOffsetUtils:
    """ノードオフセット処理ユーティリティ"""

    @staticmethod
    def apply_node_offsets(
        element_elem,
        nodes_data: Dict,
        start_offset_keys: Tuple[str, str, str, str] = ("offset_start_X", "offset_start_Y", "offset_start_Z", "id_node_start"),
        end_offset_keys: Tuple[str, str, str, str] = ("offset_end_X", "offset_end_Y", "offset_end_Z", "id_node_end"),
    ) -> Tuple[Dict, Dict]:
        """ノード座標にオフセットを適用して補正された座標を返す

        Args:
            element_elem: 要素のXML要素
            nodes_data: ノード情報辞書
            start_offset_keys: 開始点のオフセットキー (x, y, z, node_id)
            end_offset_keys: 終了点のオフセットキー (x, y, z, node_id)

        Returns:
            補正された開始ノードと終了ノードの座標
        """
        offset_start_x_key, offset_start_y_key, offset_start_z_key, id_node_start_key = start_offset_keys
        offset_end_x_key, offset_end_y_key, offset_end_z_key, id_node_end_key = end_offset_keys

        id_node_start = element_elem.get(id_node_start_key)
        id_node_end = element_elem.get(id_node_end_key)

        # オフセット値を取得（デフォルトは0）
        offset_start_x = float(element_elem.get(offset_start_x_key, 0))
        offset_start_y = float(element_elem.get(offset_start_y_key, 0))
        offset_start_z = float(element_elem.get(offset_start_z_key, 0))

        offset_end_x = float(element_elem.get(offset_end_x_key, 0))
        offset_end_y = float(element_elem.get(offset_end_y_key, 0))
        offset_end_z = float(element_elem.get(offset_end_z_key, 0))

        # 元のノード座標を取得
        original_start_node = nodes_data[id_node_start]
        original_end_node = nodes_data[id_node_end]

        # オフセットを適用した座標を計算
        corrected_start_node = {
            "x": original_start_node["x"] + offset_start_x,
            "y": original_start_node["y"] + offset_start_y,
            "z": original_start_node["z"] + offset_start_z,
        }

        corrected_end_node = {
            "x": original_end_node["x"] + offset_end_x,
            "y": original_end_node["y"] + offset_end_y,
            "z": original_end_node["z"] + offset_end_z,
        }

        logger.debug("%s にオフセットを適用", element_elem.get("id"))
        logger.debug(
            "  Start node %s: %s + (%s, %s, %s) = %s",
            id_node_start,
            original_start_node,
            offset_start_x,
            offset_start_y,
            offset_start_z,
            corrected_start_node,
        )
        logger.debug(
            "  End node %s: %s + (%s, %s, %s) = %s",
            id_node_end,
            original_end_node,
            offset_end_x,
            offset_end_y,
            offset_end_z,
            corrected_end_node,
        )

        return corrected_start_node, corrected_end_node

    @staticmethod
    def apply_vertical_node_offsets(
        element_elem,
        nodes_data: Dict,
        bottom_offset_keys: Tuple[str, str, str, str] = ("offset_bottom_X", "offset_bottom_Y", "offset_bottom_Z", "id_node_bottom"),
        top_offset_keys: Tuple[str, str, str, str] = ("offset_top_X", "offset_top_Y", "offset_top_Z", "id_node_top"),
    ) -> Tuple[Dict, Dict]:
        """垂直要素のノード座標にオフセットを適用

        Args:
            element_elem: 要素のXML要素
            nodes_data: ノード情報辞書
            bottom_offset_keys: 下端点のオフセットキー (x, y, z, node_id)
            top_offset_keys: 上端点のオフセットキー (x, y, z, node_id)

        Returns:
            補正された下端ノードと上端ノードの座標
        """
        return NodeOffsetUtils.apply_node_offsets(
            element_elem, nodes_data, bottom_offset_keys, top_offset_keys
        )


class ElementValidator:
    """要素データ検証ユーティリティ"""

    @staticmethod
    def validate_element_data(
        element_id: str,
        element_name: str,
        required_nodes: List[str],
        required_sections: List[str],
        nodes_data: Dict,
        sections_data: Dict,
    ) -> bool:
        """要素データの妥当性を確認

        Args:
            element_id: 要素ID
            element_name: 要素名（ログ用）
            required_nodes: 必要なノードIDリスト
            required_sections: 必要な断面IDリスト
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書

        Returns:
            データが揃っている場合True、不足している場合False
        """
        missing_parts = []

        # ノード検証
        for node_id in required_nodes:
            if node_id not in nodes_data:
                missing_parts.append(f"node {node_id}")

        # 断面検証
        for section_id in required_sections:
            if section_id not in sections_data:
                missing_parts.append(f"section {section_id}")

        if missing_parts:
            logger.warning(
                "%s '%s' の処理をスキップしました（%s の情報が不足）",
                element_name,
                element_id,
                ", ".join(missing_parts),
            )
            return False

        return True


class AngleUtils:
    """角度変換ユーティリティ"""

    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        """度をラジアンに変換

        Args:
            degrees: 角度（度）

        Returns:
            角度（ラジアン）
        """
        return math.radians(degrees)

    @staticmethod
    def radians_to_degrees(radians: float) -> float:
        """ラジアンを度に変換

        Args:
            radians: 角度（ラジアン）

        Returns:
            角度（度）
        """
        return math.degrees(radians)


class StoryMappingUtils:
    """階層マッピングユーティリティ"""

    @staticmethod
    def create_node_story_map(xml_parser) -> Dict[str, str]:
        """ノードIDと階層名のマッピングを作成
        
        Args:
            xml_parser: STBXMLParserインスタンス
            
        Returns:
            ノードIDをキー、階層名を値とする辞書
        """
        node_story_map = {}

        # StbStoriesを取得
        stories_element = xml_parser.find_element(".//stb:StbStories")
        if stories_element is None:
            logger.warning("StbStories 要素が見つかりません")
            return node_story_map

        namespaces = xml_parser.get_namespaces()

        # 各階層のノードIDを収集
        for story_elem in stories_element.findall("stb:StbStory", namespaces):
            story_name = story_elem.get("name", "Unknown")

            # StbNodeIdListを検索
            node_id_list = story_elem.find("stb:StbNodeIdList", namespaces)
            if node_id_list is not None:
                for node_id_elem in node_id_list.findall("stb:StbNodeId", namespaces):
                    node_id = node_id_elem.get("id")
                    if node_id:
                        node_story_map[node_id] = story_name

        logger.debug(f"階層-ノードマッピングを作成: {len(node_story_map)}個のノード")
        return node_story_map