# footing_section_extractor.py
from typing import Dict, Optional
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger

logger = get_logger(__name__)


class FootingSectionExtractor(BaseSectionExtractor):
    """ST-Bridge フーチング断面情報の抽出を担当するクラス"""

    def extract_sections(self) -> Dict[str, Dict]:
        """フーチング断面情報を抽出"""
        sections_element = self.find_element(".//stb:StbSections")
        if sections_element is None:
            logger.info("StbSections 要素が見つかりません")
            return {}

        # 共通メソッドを使用してRC基礎断面を抽出
        sections_data = self.extract_rc_sections_generic(
            sections_element,
            ".//stb:StbSecFoundation_RC",
            self._process_foundation_section,
        )

        logger.info("抽出されたフーチング断面数: %d", len(sections_data))
        return sections_data

    def _process_foundation_section(
        self, sec_elem, sections_element, namespaces
    ) -> Optional[Dict]:
        """個別のフーチング断面を処理"""
        sec_id = sec_elem.get("id")
        sec_name = sec_elem.get("name")

        # StbSecFoundation_RC要素からstrength_concrete属性を取得
        strength_concrete = sec_elem.get("strength_concrete")

        # 基礎断面図形の処理
        figure_elem = sec_elem.find("stb:StbSecFigureFoundation_RC", namespaces)
        if figure_elem is None:
            logger.warning(
                "StbSecFigureFoundation_RC が見つかりません (Section ID %s)",
                sec_id,
            )
            return None

        # 矩形基礎断面の処理
        rect_elem = figure_elem.find("stb:StbSecFoundation_RC_Rect", namespaces)
        if rect_elem is not None:
            section_dict = self._extract_foundation_rc_rect(rect_elem)
            if section_dict:
                section_dict["id"] = sec_id
                section_dict["stb_name"] = sec_name

                # コンクリート強度が指定されている場合は追加
                if strength_concrete:
                    section_dict["strength_concrete"] = strength_concrete
                    logger.debug(
                        "フーチング ID %s にコンクリート強度を設定: %s",
                        sec_id,
                        strength_concrete,
                    )

                logger.debug(
                    "RC矩形基礎断面を抽出: ID=%s, name=%s, コンクリート強度: %s",
                    sec_id,
                    sec_name,
                    strength_concrete or "未指定",
                )
                return section_dict

        # 他の基礎断面形状も将来追加可能
        logger.warning(
            "未対応の基礎断面形状です (Section ID %s)",
            sec_id,
        )
        return None

    def _extract_foundation_rc_rect(self, rect_elem) -> Optional[Dict]:
        """RC矩形基礎断面の抽出"""
        try:
            # 共通ヘルパーメソッドを使用して属性を安全に取得
            width_x = self.safe_get_float_attr(rect_elem, "width_X", 0.0)
            width_y = self.safe_get_float_attr(rect_elem, "width_Y", 0.0)
            depth = self.safe_get_float_attr(rect_elem, "depth", 0.0)

            # None チェックと値の検証
            if width_x is None or width_y is None or depth is None:
                logger.warning("RC矩形基礎断面の必須属性が取得できません")
                return None

            if width_x <= 0 or width_y <= 0 or depth <= 0:
                logger.warning(
                    "RC矩形基礎断面の寸法が無効です: width_X=%.1f, width_Y=%.1f, depth=%.1f",
                    width_x,
                    width_y,
                    depth,
                )
                return None

            return {
                "section_type": "RECTANGLE",
                "width_X": width_x,
                "width_Y": width_y,
                "width_x": width_x,  # IFC変換用
                "width_y": width_y,  # IFC変換用
                "depth": depth,
                "thickness": depth,  # フーチング厚さとして使用
            }

        except Exception as e:
            logger.warning("RC矩形基礎断面の解析に失敗しました: %s", e)
            return None
