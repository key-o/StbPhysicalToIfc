# pile_section_extractor.py
"""ST-Bridge 杭断面情報抽出クラス"""

from typing import Dict, Optional
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger

logger = get_logger(__name__)


class PileSectionExtractor(BaseSectionExtractor):
    """ST-Bridge 杭断面情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        """杭断面情報を抽出"""
        sections_data: Dict[str, Dict] = {}
        sections_element = self.find_element(".//stb:StbSections")
        if sections_element is None:
            logger.warning("StbSections 要素が見つかりません")
            return sections_data

        # 各杭タイプの抽出設定
        pile_configs = [
            {
                "xpath": ".//stb:StbSecPileProduct",
                "figure_elem": "stb:StbSecFigurePileProduct",
                "child_tags": [
                    "StbSecPileProduct_SC",
                    "StbSecPileProduct_PHC",
                    "StbSecPileProduct_PC",
                    "StbSecPileProduct_ST",
                ],
                "diameter_attr": "D",
            },
            {
                "xpath": ".//stb:StbSecPile_RC",
                "figure_elem": "stb:StbSecFigurePile_RC",
                "child_tags": [
                    "StbSecPile_RC_Straight",
                    "StbSecPile_RC_ExtendedFoot",
                    "StbSecPile_RC_ExtendedTop",
                    "StbSecPile_RC_ExtendedTopFoot",
                ],
                "diameter_attr": ["D", "D_axial"],
            },
            {
                "xpath": ".//stb:StbSecPile_S",
                "figure_elem": "stb:StbSecFigurePile_S",
                "child_tags": [
                    "StbSecPile_S_Straight",
                    "StbSecPile_S_Rotational",
                    "StbSecPile_S_Taper",
                ],
                "diameter_attr": "D",
            },
        ]

        # 統一された抽出処理
        for config in pile_configs:
            pile_sections = self._extract_pile_sections_generic(
                sections_element, config
            )
            sections_data.update(pile_sections)

        return sections_data

    def _extract_pile_sections_generic(
        self, sections_element, config: dict
    ) -> Dict[str, Dict]:
        """杭断面の汎用抽出メソッド"""
        namespaces = self.get_namespaces()
        sections_data = {}

        for sec_elem in sections_element.findall(config["xpath"], namespaces):
            sec_id = sec_elem.get("id")
            sec_name = sec_elem.get("name")

            diameter = self._parse_diameter_generic(sec_elem, config)
            if sec_id and diameter:
                sections_data[sec_id] = {
                    "section_type": "CIRCLE",
                    "radius": diameter / 2.0,
                    "stb_name": sec_name,
                }

        return sections_data

    def _parse_diameter_generic(self, sec_elem, config: dict) -> Optional[float]:
        """杭断面の直径を汎用的に解析"""
        namespaces = self.get_namespaces()
        figure = sec_elem.find(config["figure_elem"], namespaces)
        if figure is None:
            return None

        for tag in config["child_tags"]:
            child = figure.find(f"stb:{tag}", namespaces)
            if child is not None:
                # 複数の属性名を試行
                diameter_attrs = config["diameter_attr"]
                if isinstance(diameter_attrs, str):
                    diameter_attrs = [diameter_attrs]

                for attr in diameter_attrs:
                    d = child.get(attr)
                    if d:
                        try:
                            return float(d)
                        except ValueError:
                            logger.warning("杭断面の直径を解析できません: %s", d)
                            continue
        return None
