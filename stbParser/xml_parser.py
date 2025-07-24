# xml_parser.py
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import logging


logger = logging.getLogger(__name__)


class STBXMLParser:
    """ST-Bridge XML解析を担当するクラス"""

    def __init__(self, xml_string: str):
        """
        Args:
            xml_string: ST-Bridge XMLファイルの内容
        """
        self.xml_string = xml_string
        self.root = None
        self.namespaces = {}

    def parse(self) -> bool:
        """XMLを解析し、ルート要素と名前空間を設定

        Returns:
            解析成功時True、失敗時False
        """
        try:
            # ルート要素の設定
            self.root = ET.fromstring(self.xml_string)

            # 名前空間の取得
            if "}" in self.root.tag:
                # 名前空間が存在する場合
                stb_namespace_uri = self.root.tag.split("}")[0][1:]
                # Allow omitting the `stb:` prefix by mapping the namespace URI
                # to both "stb" and the empty string
                self.namespaces = {"stb": stb_namespace_uri, "": stb_namespace_uri}
            else:
                # 名前空間が存在しない場合は空の辞書
                self.namespaces = {}

            return True

        except ET.ParseError as e:
            logger.error("XML Parse Error: %s", e)
            return False

    def find_element(self, xpath: str) -> Optional[ET.Element]:
        """指定されたXPathで要素を検索

        Args:
            xpath: 検索するXPath

        Returns:
            見つかった要素、または None
        """
        if self.root is None:
            return None

        # 名前空間がない場合は、stb:プレフィックスを削除して検索
        if not self.namespaces:
            xpath_no_ns = xpath.replace("stb:", "")
            return self.root.find(xpath_no_ns)

        return self.root.find(xpath, self.namespaces)

    def find_elements(self, xpath: str) -> list:
        """指定されたXPathで複数の要素を検索

        Args:
            xpath: 検索するXPath

        Returns:
            見つかった要素のリスト
        """
        if self.root is None:
            return []

        # 名前空間がない場合は、stb:プレフィックスを削除して検索
        if not self.namespaces:
            xpath_no_ns = xpath.replace("stb:", "")
            return self.root.findall(xpath_no_ns)

        return self.root.findall(xpath, self.namespaces)

    def get_namespaces(self) -> Dict[str, str]:
        """名前空間辞書を取得

        Returns:
            名前空間辞書
        """
        return self.namespaces

    def get_root(self) -> Optional[ET.Element]:
        """ルート要素を取得

        Returns:
            ルート要素
        """
        return self.root
