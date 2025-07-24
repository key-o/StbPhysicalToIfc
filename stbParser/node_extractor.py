# node_extractor.py
from typing import Dict
from .xml_parser import STBXMLParser
from utils.logger import get_logger


logger = get_logger(__name__)


class NodeExtractor:
    """ST-Bridgeノード情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        """
        Args:
            xml_parser: 初期化済みのSTBXMLParserインスタンス
        """
        self.xml_parser = xml_parser

    def extract_nodes(self) -> Dict[str, Dict[str, float]]:
        """ST-Bridgeからノード情報を抽出

        Returns:
            ノード辞書 {node_id: {'x': x, 'y': y, 'z': z}}
        """
        nodes_data = {}

        stb_nodes_element = self.xml_parser.find_element(".//stb:StbNodes")
        if stb_nodes_element is None:
            logger.warning("StbNodes 要素が見つかりません")
            return nodes_data

        for node_elem in stb_nodes_element.findall(
            "stb:StbNode", self.xml_parser.get_namespaces()
        ):
            node_id = node_elem.get("id")
            if not node_id:
                continue

            try:
                x = float(node_elem.get("X"))
                y = float(node_elem.get("Y"))
                z = float(node_elem.get("Z"))
                nodes_data[node_id] = {"x": x, "y": y, "z": z}
            except (TypeError, ValueError) as e:
                logger.warning(
                    "ノード ID %s の座標を解析できません: %s",
                    node_id,
                    e,
                )
                continue

        return nodes_data
