# brace_section_extractor.py
from typing import Dict, Optional
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger

logger = get_logger(__name__)


class BraceSectionExtractor(BaseSectionExtractor):
    """Extractor for brace section information."""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        sections_data: Dict[str, Dict] = {}
        sections_element = self.find_element(".//stb:StbSections")
        if sections_element is None:
            logger.warning("Brace用のStbSections要素が見つかりません")
            return sections_data

        # 共通メソッドを使用してブレース断面を抽出
        return self.extract_steel_sections_generic(
            sections_element, ".//stb:StbSecBrace_S", self._process_brace_section
        )

    def _process_brace_section(
        self, sec_elem, sections_element, namespaces
    ) -> Optional[Dict]:
        """個別のブレース断面を処理"""
        sec_id = sec_elem.get("id")
        sec_name = sec_elem.get("name")

        # Same構成の鋼材要素を検索
        same_info = self.find_same_steel_element(
            sec_elem,
            ".//stb:StbSecSteelFigureBrace_S/stb:StbSecSteelBrace_S_Same",
            namespaces,
        )

        if same_info is None:
            logger.warning("Brace断面ID %s は未対応の構成です", sec_id)
            return None

        # 共通メソッドを使用して鋼材形状パラメータを取得
        sec_dict = self.process_steel_shape_params(same_info["steel_elem"], sec_name)

        if sec_dict:
            sec_dict["strength_main"] = same_info["strength_main"]
            sec_dict["stb_name"] = sec_name
            logger.debug(
                "Brace断面 %s を解析しました: %s", sec_id, same_info["shape_name"]
            )

        return sec_dict
