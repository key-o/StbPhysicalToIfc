"""ST-Bridge スラブ断面情報抽出クラス"""

from typing import Dict, Optional
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger

logger = get_logger(__name__)


class SlabSectionExtractor(BaseSectionExtractor):
    """ST-Bridge スラブ断面情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        """スラブ断面情報を抽出（RC + デッキスラブ）"""
        sections_element = self.find_element(".//stb:StbSections")
        if sections_element is None:
            logger.info("StbSections 要素が見つかりません")
            return {}

        # RCスラブ断面を抽出
        rc_sections = self.extract_rc_sections_generic(
            sections_element, ".//stb:StbSecSlab_RC", self._process_slab_section
        )

        # デッキスラブ断面を抽出
        deck_sections = self.extract_deck_sections_generic(
            sections_element, ".//stb:StbSecSlabDeck", self._process_slab_deck_section
        )

        # 両方の結果をマージ
        all_sections = rc_sections.copy()
        all_sections.update(deck_sections)

        return all_sections

    def _process_slab_section(
        self, sec_elem, sections_element, namespaces
    ) -> Optional[Dict]:
        """個別のスラブ断面を処理"""
        sec_id = sec_elem.get("id")
        sec_name = sec_elem.get("name")

        # StbSecSlab_RC要素からstrength_concrete属性を取得
        strength_concrete = sec_elem.get("strength_concrete")

        # まずストレート断面を確認
        depth_elem = sec_elem.find(
            "stb:StbSecFigureSlab_RC/stb:StbSecSlab_RC_Straight", namespaces
        )
        
        depth = None
        section_type = "RECTANGLE"
        
        if depth_elem is not None:
            # ストレート断面の場合
            depth = self.safe_get_float_attr(depth_elem, "depth")
        else:
            # テーパー断面を確認
            taper_elements = sec_elem.findall(
                "stb:StbSecFigureSlab_RC/stb:StbSecSlab_RC_Taper", namespaces
            )
            
            if taper_elements:
                # テーパー断面の場合：BASE（厚い方）の値を使用
                base_elem = None
                tip_elem = None
                
                for taper_elem in taper_elements:
                    pos = taper_elem.get("pos")
                    if pos == "BASE":
                        base_elem = taper_elem
                    elif pos == "TIP":
                        tip_elem = taper_elem
                
                if base_elem is not None:
                    depth = self.safe_get_float_attr(base_elem, "depth")
                    section_type = "TAPER"
                    logger.debug(
                        "スラブ断面 ID %s でテーパー断面を検出、BASE深度を使用: %s", 
                        sec_id, depth
                    )
                elif tip_elem is not None:
                    # BASEがない場合はTIPを使用
                    depth = self.safe_get_float_attr(tip_elem, "depth")
                    section_type = "TAPER"
                    logger.debug(
                        "スラブ断面 ID %s でテーパー断面を検出、TIP深度を使用: %s", 
                        sec_id, depth
                    )

        if depth is None:
            logger.warning(
                "スラブ断面 ID %s で深さ情報が取得できません（ストレート・テーパー断面共に確認済み）", 
                sec_id
            )
            return None

        result = {
            "section_type": section_type,
            "thickness": depth,
            "stb_name": sec_name,
        }

        # コンクリート強度が指定されている場合は追加
        if strength_concrete:
            result["strength_concrete"] = strength_concrete
            logger.debug(
                "スラブ ID %s にコンクリート強度を設定: %s", sec_id, strength_concrete
            )

        return result

    def extract_deck_sections_generic(
        self, sections_element, xpath: str, process_func
    ) -> Dict[str, Dict]:
        """デッキスラブ断面を抽出する汎用メソッド"""
        sections = {}
        namespaces = self.get_namespaces()

        for sec_elem in sections_element.findall(xpath, namespaces):
            sec_id = sec_elem.get("id")
            if sec_id:
                section_data = process_func(sec_elem, sections_element, namespaces)
                if section_data:
                    sections[sec_id] = section_data
                    logger.debug(
                        "デッキスラブ断面を抽出: ID=%s, 名前=%s",
                        sec_id,
                        section_data.get("stb_name"),
                    )

        logger.info("デッキスラブ断面抽出完了: %d件", len(sections))
        return sections

    def _process_slab_deck_section(
        self, sec_elem, sections_element, namespaces
    ) -> Optional[Dict]:
        """個別のデッキスラブ断面を処理"""
        sec_id = sec_elem.get("id")
        sec_name = sec_elem.get("name")
        product_type = sec_elem.get("product_type", "FLAT")

        # StbSecFigureSlabDeck内のStbSecSlabDeckStraightから深さを取得
        depth_elem = sec_elem.find(
            "stb:StbSecFigureSlabDeck/stb:StbSecSlabDeckStraight", namespaces
        )

        if depth_elem is None:
            logger.warning(
                "デッキスラブ断面 ID %s で StbSecSlabDeckStraight が見つかりません",
                sec_id,
            )
            return None

        # デッキスラブの厚さを取得
        depth = self.safe_get_float_attr(depth_elem, "depth")

        if depth is None:
            logger.warning("デッキスラブ断面 ID %s で深さ情報が取得できません", sec_id)
            return None

        # デッキ製品情報も取得（オプション）
        product_elem = sec_elem.find("stb:StbSecProductSlabDeck", namespaces)
        product_code = "Undefined"
        depth_deck = 0.0

        if product_elem is not None:
            product_code = product_elem.get("product_code", "Undefined")
            depth_deck = self.safe_get_float_attr(product_elem, "depth_deck") or 0.0

        logger.debug(
            "デッキスラブ断面処理: ID=%s, 名前=%s, product_type=%s, depth=%s, product_code=%s, depth_deck=%s",
            sec_id,
            sec_name,
            product_type,
            depth,
            product_code,
            depth_deck,
        )

        return {
            "section_type": "SLAB_DECK",
            "thickness": depth,
            "product_type": product_type,
            "product_code": product_code,
            "depth_deck": depth_deck,
            "stb_name": sec_name,
        }
