# src_section_extractor.py
"""
SRC (Steel Reinforced Concrete) 断面抽出器
RC と Steel の複合断面を処理
"""
from typing import Dict, Optional
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger

logger = get_logger(__name__)


class SRCSectionExtractor(BaseSectionExtractor):
    """SRC構造断面情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        """ST-BridgeからSRC断面情報を抽出

        Returns:
            断面辞書 {section_id: section_info}
        """
        sections_data = {}

        stb_sections_element = self.find_element(".//stb:StbSections")
        if stb_sections_element is None:
            logger.warning("StbSections element not found.")
            return sections_data

        # SRC構造柱断面の処理
        self._extract_src_column_sections(stb_sections_element, sections_data)
        
        # SRC構造梁断面の処理
        self._extract_src_beam_sections(stb_sections_element, sections_data)

        return sections_data

    def _extract_src_column_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """SRC構造柱断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_src_elem in sections_element.findall(".//stb:StbSecColumn_SRC", namespaces):
            sec_id = sec_src_elem.get("id")
            sec_name = sec_src_elem.get("name")
            strength_concrete = sec_src_elem.get("strength_concrete", "Fc21")

            if not sec_id:
                continue

            logger.debug("SRC柱断面 ID %s を検出 (名称: %s)", sec_id, sec_name)

            # RC断面部分の抽出
            rc_info = self._extract_src_rc_section(sec_src_elem, namespaces)
            
            # 鋼材断面部分の抽出
            steel_info = self._extract_src_steel_section(sec_src_elem, namespaces)
            
            # 鉄筋情報の抽出
            rebar_info = self._extract_src_rebar_section(sec_src_elem, namespaces)

            if rc_info and steel_info:
                # SRC複合断面として統合
                src_section_info = {
                    "section_type": "SRC_COMPOSITE",
                    "stb_structure_type": "SRC",
                    "stb_name": sec_name,
                    "strength_concrete": strength_concrete,
                    "rc_section": rc_info,
                    "steel_section": steel_info,
                    "rebar_section": rebar_info
                }
                
                sections_data[sec_id] = src_section_info
                logger.debug(
                    "SRC柱断面 ID %s を解析しました: RC=%s, Steel=%s",
                    sec_id,
                    rc_info.get("section_type"),
                    steel_info.get("section_type")
                )
            else:
                logger.warning("SRC柱断面 ID %s の構成要素が不完全です", sec_id)

    def _extract_src_beam_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """SRC構造梁断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_src_elem in sections_element.findall(".//stb:StbSecBeam_SRC", namespaces):
            sec_id = sec_src_elem.get("id")
            sec_name = sec_src_elem.get("name")
            strength_concrete = sec_src_elem.get("strength_concrete", "Fc21")

            if not sec_id:
                continue

            logger.debug("SRC梁断面 ID %s を検出 (名称: %s)", sec_id, sec_name)

            # RC断面部分の抽出
            rc_info = self._extract_src_rc_beam_section(sec_src_elem, namespaces)
            
            # 鋼材断面部分の抽出
            steel_info = self._extract_src_steel_beam_section(sec_src_elem, namespaces)
            
            # 鉄筋情報の抽出
            rebar_info = self._extract_src_rebar_beam_section(sec_src_elem, namespaces)

            if rc_info and steel_info:
                # SRC複合断面として統合
                src_section_info = {
                    "section_type": "SRC_COMPOSITE",
                    "stb_structure_type": "SRC",
                    "stb_name": sec_name,
                    "strength_concrete": strength_concrete,
                    "rc_section": rc_info,
                    "steel_section": steel_info,
                    "rebar_section": rebar_info
                }
                
                sections_data[sec_id] = src_section_info
                logger.debug(
                    "SRC梁断面 ID %s を解析しました: RC=%s, Steel=%s",
                    sec_id,
                    rc_info.get("section_type"),
                    steel_info.get("section_type")
                )
            else:
                logger.warning("SRC梁断面 ID %s の構成要素が不完全です", sec_id)

    def _extract_src_rc_section(self, src_elem, namespaces) -> Optional[Dict]:
        """SRC柱のRC断面部分を抽出"""
        rc_fig = src_elem.find(".//stb:StbSecFigureColumn_SRC", namespaces)
        if rc_fig is None:
            logger.warning("StbSecFigureColumn_SRC が見つかりません")
            return None

        # 矩形断面
        rect_elem = rc_fig.find("stb:StbSecColumn_SRC_Rect", namespaces)
        if rect_elem is not None:
            width_x = self._float_attr(rect_elem, "width_X")
            width_y = self._float_attr(rect_elem, "width_Y")
            
            if width_x and width_y:
                return {
                    "section_type": "RECTANGLE",
                    "width_x": width_x,
                    "width_y": width_y,
                    "material_type": "RC"
                }

        # 円形断面
        circle_elem = rc_fig.find("stb:StbSecColumn_SRC_Circle", namespaces)
        if circle_elem is not None:
            diameter = self._float_attr(circle_elem, "D")
            
            if diameter:
                return {
                    "section_type": "CIRCLE",
                    "radius": diameter / 2.0,
                    "material_type": "RC"
                }

        logger.warning("対応するRC断面形状が見つかりません")
        return None

    def _extract_src_steel_section(self, src_elem, namespaces) -> Optional[Dict]:
        """SRC柱の鋼材断面部分を抽出"""
        steel_fig = src_elem.find(".//stb:StbSecSteelFigureColumn_SRC", namespaces)
        if steel_fig is None:
            logger.warning("StbSecSteelFigureColumn_SRC が見つかりません")
            return None

        logger.warning("StbSecSteelFigureColumn_SRC を検出しました")

        # Same構成の処理
        same_elem = steel_fig.find("stb:StbSecSteelColumn_SRC_Same", namespaces)
        if same_elem is not None:
            logger.warning("StbSecSteelColumn_SRC_Same を検出しました")
            return self._extract_src_same_steel_section(same_elem, namespaces)
        
        # NotSame構成の処理
        notsame_elem = steel_fig.find("stb:StbSecSteelColumn_SRC_NotSame", namespaces)
        if notsame_elem is not None:
            logger.warning("StbSecSteelColumn_SRC_NotSame を検出しました（未対応）")
            return None

        logger.warning("SRC steel figure structure not recognized")
        return None

    def _extract_src_same_steel_section(self, same_elem, namespaces) -> Optional[Dict]:
        """SRC Same構成の鋼材断面を抽出"""
        
        child_tags = [child.tag.split('}')[-1] if '}' in child.tag else child.tag for child in same_elem]
        logger.warning("SRC Same構成の子要素を検索中: %s", child_tags)
        
        # H断面
        h_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeH", namespaces)
        if h_elem is not None:
            shape_name = h_elem.get("shape")
            encase_type = h_elem.get("encase_type", "ENCASEDANDINFILLED")
            strength = h_elem.get("strength", "SN400B")
            
            if shape_name:
                logger.warning("H断面形状名を検索中: %s", shape_name)
                logger.warning("利用可能な鋼材断面キャッシュ: %s", list(self._steel_section_cache.keys()))
                steel_elem = self.find_steel_section_by_name(None, shape_name)
                if steel_elem is not None:
                    logger.debug("H鋼材要素が見つかりました: %s", shape_name)
                    h_info = self.extract_h_steel_section(steel_elem)
                    if h_info:
                        h_info["encase_type"] = encase_type
                        h_info["strength_main"] = strength
                        h_info["steel_shape_name"] = shape_name
                        return h_info
                else:
                    logger.warning("H鋼材要素が見つかりません: %s", shape_name)
        
        # BOX断面
        box_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeBox", namespaces)
        if box_elem is not None:
            shape_name = box_elem.get("shape")
            encase_type = box_elem.get("encase_type", "ENCASEDANDINFILLED")
            strength = box_elem.get("strength", "BCR295")
            
            logger.warning("BOX断面検索: shape=%s", repr(shape_name))
            if shape_name:
                steel_elem = self.find_steel_section_by_name(None, shape_name)
                logger.warning("BOX鋼材要素: %s", steel_elem is not None)
                if steel_elem is not None:
                    box_info = self.extract_box_steel_section(steel_elem)
                    if box_info:
                        box_info["encase_type"] = encase_type
                        box_info["strength_main"] = strength
                        box_info["steel_shape_name"] = shape_name
                        return box_info

        # PIPE断面
        pipe_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapePipe", namespaces)
        if pipe_elem is not None:
            shape_name = pipe_elem.get("shape")
            encase_type = pipe_elem.get("encase_type", "ENCASEDANDINFILLED")
            strength = pipe_elem.get("strength", "SN400B")
            
            logger.warning("PIPE断面検索: shape=%s", repr(shape_name))
            if shape_name:
                steel_elem = self.find_steel_section_by_name(None, shape_name)
                logger.warning("PIPE鋼材要素: %s", steel_elem is not None)
                if steel_elem is not None:
                    pipe_info = self.extract_pipe_steel_section(steel_elem)
                    if pipe_info:
                        pipe_info["encase_type"] = encase_type
                        pipe_info["strength_main"] = strength
                        pipe_info["steel_shape_name"] = shape_name
                        return pipe_info

        # T断面（十字配置）
        t_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeT", namespaces)
        if t_elem is not None:
            return self._extract_src_t_section(t_elem)

        # Cross断面（クロス配置）
        cross_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeCross", namespaces)
        if cross_elem is not None:
            logger.warning("Cross断面要素を検出: %s", cross_elem.attrib)
            return self._extract_src_cross_section(cross_elem)

        logger.warning("対応するSRC鋼材断面形状が見つかりません (Same構成)")
        return None

    def _extract_src_t_section(self, t_elem) -> Optional[Dict]:
        """SRC T断面（十字配置）を抽出"""
        direction_type = t_elem.get("direction_type")
        shape_h = t_elem.get("shape_H")
        shape_t = t_elem.get("shape_T")
        strength_h = t_elem.get("strength_main_H", "SN400B")
        strength_t = t_elem.get("strength_main_T", "SN400B")
        
        if not (shape_h and shape_t):
            logger.warning("T断面のshape_Hまたはshape_Tが不足しています")
            return None

        # H断面要素を取得
        h_steel_elem = self.find_steel_section_by_name(None, shape_h)
        t_steel_elem = self.find_steel_section_by_name(None, shape_t)
        
        if h_steel_elem is None or t_steel_elem is None:
            logger.warning("T断面の鋼材要素が見つかりません: H=%s, T=%s", shape_h, shape_t)
            return None

        h_info = self.extract_h_steel_section(h_steel_elem)
        t_info = self.extract_h_steel_section(t_steel_elem)
        
        if h_info and t_info:
            return {
                "section_type": "T_COMPOSITE",
                "direction_type": direction_type,
                "h_section": {**h_info, "steel_shape_name": shape_h, "strength_main": strength_h},
                "t_section": {**t_info, "steel_shape_name": shape_t, "strength_main": strength_t}
            }
        
        return None

    def _extract_src_cross_section(self, cross_elem) -> Optional[Dict]:
        """SRC Cross断面（クロス配置）を抽出"""
        direction_type = cross_elem.get("direction_type")
        # Cross断面ではshape_Xとshape_Yが使用される
        shape_h1 = cross_elem.get("shape_X")
        shape_h2 = cross_elem.get("shape_Y") 
        strength_h1 = cross_elem.get("strength_main_X", "SN400B")
        strength_h2 = cross_elem.get("strength_main_Y", "SN400B")
        
        if not (shape_h1 and shape_h2):
            logger.warning("Cross断面のshape_Xまたはshape_Yが不足しています")
            return None

        logger.warning("Cross断面の形状名: X=%s, Y=%s", shape_h1, shape_h2)
        
        # H断面要素を取得
        h1_steel_elem = self.find_steel_section_by_name(None, shape_h1)
        h2_steel_elem = self.find_steel_section_by_name(None, shape_h2)
        
        if h1_steel_elem is None or h2_steel_elem is None:
            logger.warning("Cross断面の鋼材要素が見つかりません: X=%s, Y=%s", shape_h1, shape_h2)
            return None

        h1_info = self.extract_h_steel_section(h1_steel_elem)
        h2_info = self.extract_h_steel_section(h2_steel_elem)
        
        if h1_info and h2_info:
            return {
                "section_type": "CROSS_COMPOSITE",
                "direction_type": direction_type,
                "h1_section": {**h1_info, "steel_shape_name": shape_h1, "strength_main": strength_h1},
                "h2_section": {**h2_info, "steel_shape_name": shape_h2, "strength_main": strength_h2}
            }
        
        return None

    def _extract_src_rebar_section(self, src_elem, namespaces) -> Optional[Dict]:
        """SRC柱の鉄筋情報を抽出"""
        rebar_elem = src_elem.find(".//stb:StbSecBarArrangementColumn_SRC", namespaces)
        if rebar_elem is None:
            return None

        # かぶり厚情報
        cover_start_x = self._float_attr(rebar_elem, "depth_cover_start_X")
        cover_end_x = self._float_attr(rebar_elem, "depth_cover_end_X")
        cover_start_y = self._float_attr(rebar_elem, "depth_cover_start_Y")
        cover_end_y = self._float_attr(rebar_elem, "depth_cover_end_Y")
        kind_corner = rebar_elem.get("kind_corner", "NONE")

        # 配筋情報
        bar_elem = rebar_elem.find("stb:StbSecBarColumn_SRC_RectSame", namespaces)
        if bar_elem is not None:
            return {
                "cover_start_x": cover_start_x,
                "cover_end_x": cover_end_x,
                "cover_start_y": cover_start_y,
                "cover_end_y": cover_end_y,
                "kind_corner": kind_corner,
                "d_main": bar_elem.get("D_main"),
                "d_band": bar_elem.get("D_band"),
                "strength_main": bar_elem.get("strength_main"),
                "strength_band": bar_elem.get("strength_band"),
                "n_main_x_1st": self._float_attr(bar_elem, "N_main_X_1st"),
                "n_main_y_1st": self._float_attr(bar_elem, "N_main_Y_1st"),
                "n_main_total": self._float_attr(bar_elem, "N_main_total"),
                "pitch_band": self._float_attr(bar_elem, "pitch_band"),
                "n_band_direction_x": self._float_attr(bar_elem, "N_band_direction_X"),
                "n_band_direction_y": self._float_attr(bar_elem, "N_band_direction_Y")
            }

        return None

    def _extract_src_rc_beam_section(self, src_elem, namespaces) -> Optional[Dict]:
        """SRC梁のRC断面部分を抽出"""
        rc_fig = src_elem.find(".//stb:StbSecFigureBeam_SRC", namespaces)
        if rc_fig is None:
            logger.warning("StbSecFigureBeam_SRC が見つかりません")
            return None

        # 矩形断面
        rect_elem = rc_fig.find("stb:StbSecBeam_SRC_Rect", namespaces)
        if rect_elem is not None:
            width = self._float_attr(rect_elem, "width")
            depth = self._float_attr(rect_elem, "depth")
            
            if width and depth:
                return {
                    "section_type": "RECTANGLE",
                    "width": width,
                    "height": depth,
                    "material_type": "RC"
                }

        logger.warning("対応するSRC梁RC断面形状が見つかりません")
        return None

    def _extract_src_steel_beam_section(self, src_elem, namespaces) -> Optional[Dict]:
        """SRC梁の鋼材断面部分を抽出"""
        steel_fig = src_elem.find(".//stb:StbSecSteelFigureBeam_SRC", namespaces)
        if steel_fig is None:
            logger.warning("StbSecSteelFigureBeam_SRC が見つかりません")
            return None

        # Same構成の処理
        same_elem = steel_fig.find("stb:StbSecSteelBeam_SRC_Same", namespaces)
        if same_elem is not None:
            shape_name = same_elem.get("shape")
            strength_main = same_elem.get("strength_main", "SN400B")
            encase_type = same_elem.get("encase_type", "ENCASED")
            
            if shape_name:
                steel_elem = self.find_steel_section_by_name(None, shape_name)
                if steel_elem is not None:
                    steel_info = self.process_steel_shape_params(steel_elem, shape_name)
                    if steel_info:
                        steel_info["encase_type"] = encase_type
                        steel_info["strength_main"] = strength_main
                        steel_info["steel_shape_name"] = shape_name
                        return steel_info

        logger.warning("SRC梁鋼材断面の抽出に失敗しました")
        return None

    def _extract_src_rebar_beam_section(self, src_elem, namespaces) -> Optional[Dict]:
        """SRC梁の鉄筋情報を抽出"""
        rebar_elem = src_elem.find(".//stb:StbSecBarArrangementBeam_SRC", namespaces)
        if rebar_elem is None:
            return None

        # 基本的な鉄筋情報を抽出（詳細実装は必要に応じて拡張）
        return {
            "rebar_type": "SRC_BEAM_REBAR",
            "extracted": True
        }