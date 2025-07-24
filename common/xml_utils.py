# xml_utils.py
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List
from utils.logger import get_logger

logger = get_logger(__name__)


class XMLUtils:
    """ST-Bridge XML解析のためのユーティリティクラス"""

    @staticmethod
    def parse_xml_string(xml_string: str) -> Optional[ET.Element]:
        """XML文字列を解析してルート要素を返す
        
        Args:
            xml_string: 解析するXML文字列
            
        Returns:
            ルート要素、または解析失敗時はNone
        """
        try:
            return ET.fromstring(xml_string)
        except ET.ParseError as e:
            logger.error("XML Parse Error: %s", e)
            return None

    @staticmethod
    def extract_namespaces(root: ET.Element) -> Dict[str, str]:
        """ルート要素から名前空間を抽出
        
        Args:
            root: XML ルート要素
            
        Returns:
            名前空間辞書
        """
        if "}" in root.tag:
            stb_namespace_uri = root.tag.split("}")[0][1:]
            return {"stb": stb_namespace_uri, "": stb_namespace_uri}
        return {}

    @staticmethod
    def find_element_safe(root: ET.Element, xpath: str, namespaces: Dict[str, str]) -> Optional[ET.Element]:
        """安全な要素検索（名前空間を考慮）
        
        Args:
            root: 検索対象のルート要素
            xpath: 検索するXPath
            namespaces: 名前空間辞書
            
        Returns:
            見つかった要素、またはNone
        """
        if not namespaces:
            xpath_no_ns = xpath.replace("stb:", "")
            return root.find(xpath_no_ns)
        return root.find(xpath, namespaces)

    @staticmethod
    def find_elements_safe(root: ET.Element, xpath: str, namespaces: Dict[str, str]) -> List[ET.Element]:
        """安全な複数要素検索（名前空間を考慮）
        
        Args:
            root: 検索対象のルート要素
            xpath: 検索するXPath
            namespaces: 名前空間辞書
            
        Returns:
            見つかった要素のリスト
        """
        if not namespaces:
            xpath_no_ns = xpath.replace("stb:", "")
            return root.findall(xpath_no_ns)
        return root.findall(xpath, namespaces)

    @staticmethod
    def find_stb_members(root: ET.Element, namespaces: Dict[str, str]) -> Optional[ET.Element]:
        """StbMembers要素を検索（共通処理）
        
        Args:
            root: 検索対象のルート要素
            namespaces: 名前空間辞書
            
        Returns:
            StbMembers要素、またはNone
        """
        stb_members = XMLUtils.find_element_safe(root, ".//stb:StbMembers", namespaces)
        if stb_members is None:
            logger.warning("StbMembers 要素が見つかりません")
        return stb_members

    @staticmethod
    def validate_xml_structure(root: ET.Element, namespaces: Dict[str, str]) -> bool:
        """基本的なXML構造を検証
        
        Args:
            root: 検証対象のルート要素
            namespaces: 名前空間辞書
            
        Returns:
            構造が有効な場合True
        """
        # 基本的な構造要素の存在を確認
        required_elements = [".//stb:StbModel"]
        
        for xpath in required_elements:
            if XMLUtils.find_element_safe(root, xpath, namespaces) is None:
                logger.warning(f"必要な要素が見つかりません: {xpath}")
                return False
        
        return True