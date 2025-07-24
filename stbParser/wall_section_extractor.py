"""ST-Bridge 壁断面情報抽出クラス"""

from typing import Dict, Optional
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger

logger = get_logger(__name__)


class WallSectionExtractor(BaseSectionExtractor):
    """ST-Bridge 壁断面情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        """壁断面情報を抽出"""
        sections_element = self.find_element(".//stb:StbSections")
        if sections_element is None:
            logger.info("StbSections 要素が見つかりません")
            return {}

        # 共通メソッドを使用してRC壁断面を抽出
        return self.extract_rc_sections_generic(
            sections_element, ".//stb:StbSecWall_RC", self._process_wall_section
        )

    def _process_wall_section(
        self, sec_elem, sections_element, namespaces
    ) -> Optional[Dict]:
        """個別の壁断面を処理"""
        sec_id = sec_elem.get("id")
        sec_name = sec_elem.get("name")

        # StbSecWall_RC要素からstrength_concrete属性を取得
        strength_concrete = sec_elem.get("strength_concrete")

        t_elem = sec_elem.find(
            "stb:StbSecFigureWall_RC/stb:StbSecWall_RC_Straight", namespaces
        )

        if t_elem is None:
            logger.warning(
                "壁断面 ID %s で StbSecWall_RC_Straight が見つかりません", sec_id
            )
            return None

        # 共通ヘルパーメソッドを使用
        thickness = self.safe_get_float_attr(t_elem, "t")

        if thickness is None:
            logger.warning("壁断面 ID %s で厚さ情報が取得できません", sec_id)
            return None

        result = {
            "section_type": "RECTANGLE",
            "thickness": thickness,
            "stb_name": sec_name,
        }

        # コンクリート強度が指定されている場合は追加
        if strength_concrete:
            result["strength_concrete"] = strength_concrete
            logger.debug(
                "壁 ID %s にコンクリート強度を設定: %s", sec_id, strength_concrete
            )

        return result
