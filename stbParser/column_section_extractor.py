# column_section_extractor.py
from typing import Dict, Optional
import logging
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger


logger = get_logger(__name__)


class ColumnSectionExtractor(BaseSectionExtractor):
    """ST-Bridge柱断面情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        """ST-Bridgeから柱断面情報を抽出

        Returns:
            断面辞書 {section_id: section_info}
        """
        sections_data = {}

        stb_sections_element = self.find_element(".//stb:StbSections")
        if stb_sections_element is None:
            logger.warning("StbSections element not found.")
            return sections_data

        # 鋼構造柱断面の処理
        self._extract_steel_column_sections(stb_sections_element, sections_data)

        # RC構造柱断面の処理
        self._extract_rc_column_sections(stb_sections_element, sections_data)

        # CFT柱断面の処理
        self._extract_cft_column_sections(stb_sections_element, sections_data)

        # SRC柱断面の処理
        self._extract_src_column_sections(stb_sections_element, sections_data)

        return sections_data

    def _extract_steel_column_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """鋼構造柱断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_s_elem in sections_element.findall(".//stb:StbSecColumn_S", namespaces):
            sec_id = sec_s_elem.get("id")
            sec_name = sec_s_elem.get("name")

            if not sec_id:
                continue

            # 鋼材図形要素を取得
            steel_fig = sec_s_elem.find(".//stb:StbSecSteelFigureColumn_S", namespaces)
            if steel_fig is None:
                logger.warning("StbSecSteelFigureColumn_S not found for ID %s", sec_id)
                continue

            # 統一処理を使用してSame/NotSameパターンを処理
            context_info = {
                "sec_id": sec_id,
                "sec_name": sec_name,
                "structure_type": "S"
            }
            
            shape_processor = lambda steel_elem, elem: self._process_steel_column_shape(steel_elem, elem, context_info)
            results = self.process_same_notsame_pattern(steel_fig, shape_processor, context_info)
            
            if results:
                # 結果の処理
                if len(results) == 1:
                    # Same または単一のNotSame
                    sections_data[sec_id] = results[0]
                    logger.debug("S柱断面を解析: ID=%s", sec_id)
                elif len(results) == 2:
                    # NotSame の上下断面
                    bottom_info = next((r for r in results if r.get("position") == "BOTTOM"), None)
                    top_info = next((r for r in results if r.get("position") == "TOP"), None)
                    
                    if bottom_info and top_info:
                        if bottom_info.get("stb_shape_name") == top_info.get("stb_shape_name"):
                            # 同じ断面の場合は代表断面として使用
                            sections_data[sec_id] = bottom_info
                            logger.debug("NotSame柱断面（同じ断面）: ID=%s", sec_id)
                        else:
                            # 変断面の場合
                            sections_data[sec_id] = {
                                "section_type": "TAPERED_S",
                                "start_section": bottom_info,
                                "end_section": top_info,
                                "stb_name": sec_name,
                                "stb_structure_type": "S",
                            }
                            logger.debug("NotSame変断面柱: ID=%s", sec_id)
                    elif bottom_info:
                        sections_data[sec_id] = bottom_info
                        logger.debug("NotSame柱断面（下端のみ）: ID=%s", sec_id)
                    elif top_info:
                        sections_data[sec_id] = top_info
                        logger.debug("NotSame柱断面（上端のみ）: ID=%s", sec_id)
                continue

            # ThreeTypes柱断面の処理
            three_types_elem = steel_fig.find(
                "stb:StbSecSteelColumn_S_ThreeTypes", namespaces
            )
            if three_types_elem is not None:
                logger.debug("ThreeTypes柱断面 ID %s は現在簡易処理中", sec_id)
                # 簡易処理: 下端断面を代表断面として使用
                shape_bottom = three_types_elem.get("shape_bottom")
                shape_center = three_types_elem.get("shape_center")
                shape_top = three_types_elem.get("shape_top")
                strength_main = three_types_elem.get("strength_main")

                # 利用可能な断面を優先順位で選択
                shape_name = shape_bottom or shape_center or shape_top

                if shape_name:
                    steel_elem = self.find_steel_section_by_name(
                        sections_element, shape_name
                    )
                    if steel_elem is not None:
                        sec_dict = self._extract_steel_section_dict(steel_elem)
                        if sec_dict:
                            sec_dict["strength_main"] = strength_main
                            sec_dict["stb_name"] = sec_name
                            sec_dict["stb_shape_name"] = shape_name
                            sec_dict["stb_structure_type"] = "S"
                            sec_dict["note"] = "ThreeTypes柱断面（代表断面を使用）"
                            sections_data[sec_id] = sec_dict
                            logger.debug(
                                "ThreeTypes柱断面を簡易処理: ID=%s, shape=%s",
                                sec_id,
                                shape_name,
                            )
                continue

            logger.warning("S柱断面タイプが未対応です: Section ID %s", sec_id)

    def _process_steel_column_shape(self, steel_elem, elem, context_info: Dict) -> Optional[Dict]:
        """鋼構造柱断面の個別形状処理"""
        try:
            sec_dict = self._extract_steel_section_dict(steel_elem)
            if sec_dict:
                sec_dict["stb_name"] = context_info["sec_name"]
                sec_dict["stb_shape_name"] = elem.get("shape")
                sec_dict["stb_structure_type"] = context_info["structure_type"]
                return sec_dict
            return None
        except Exception as e:
            logger.error("鋼構造柱断面形状処理エラー: %s", e)
            return None

    def _extract_rc_column_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """RC構造柱断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_rc_elem in sections_element.findall(
            ".//stb:StbSecColumn_RC", namespaces
        ):
            sec_id = sec_rc_elem.get("id")
            sec_name = sec_rc_elem.get("name")

            if not sec_id:
                continue

            # StbSecColumn_RC要素からstrength_concrete属性を取得
            strength_concrete = sec_rc_elem.get("strength_concrete")

            # RC図形要素を取得
            rc_fig = sec_rc_elem.find(".//stb:StbSecFigureColumn_RC", namespaces)
            if rc_fig is None:
                logger.warning("StbSecFigureColumn_RC not found for ID %s", sec_id)
                continue

            # 矩形断面の処理
            rect_elem = rc_fig.find("stb:StbSecColumn_RC_Rect", namespaces)
            if rect_elem is not None:
                width = self._float_attr(rect_elem, "width_X")
                height = self._float_attr(rect_elem, "width_Y")

                if width and height:
                    rc_section_info = {
                        "section_type": "RECTANGLE",
                        "width_x": width,
                        "width_y": height,
                        "stb_name": sec_name,
                        "stb_structure_type": "RC",
                    }

                    # コンクリート強度が指定されている場合は追加
                    if strength_concrete:
                        rc_section_info["strength_concrete"] = strength_concrete
                        logger.debug(
                            "柱 ID %s にコンクリート強度を設定: %s",
                            sec_id,
                            strength_concrete,
                        )

                    sections_data[sec_id] = rc_section_info
                    logger.debug(
                        "RC矩形柱断面 ID %s を解析しました: %s x %s, コンクリート強度: %s",
                        sec_id,
                        width,
                        height,
                        strength_concrete or "未指定",
                    )
                continue

            # 円形断面の処理
            circle_elem = rc_fig.find("stb:StbSecColumn_RC_Circle", namespaces)
            if circle_elem is not None:
                diameter = self._float_attr(circle_elem, "D")

                if diameter:
                    rc_section_info = {
                        "section_type": "CIRCLE",
                        "radius": diameter / 2.0,
                        "stb_name": sec_name,
                        "stb_structure_type": "RC",
                    }

                    # コンクリート強度が指定されている場合は追加
                    if strength_concrete:
                        rc_section_info["strength_concrete"] = strength_concrete
                        logger.debug(
                            "柱 ID %s にコンクリート強度を設定: %s",
                            sec_id,
                            strength_concrete,
                        )

                    sections_data[sec_id] = rc_section_info
                    logger.debug(
                        "RC円形柱断面 ID %s を解析しました: D=%s, コンクリート強度: %s",
                        sec_id,
                        diameter,
                        strength_concrete or "未指定",
                    )
                continue

            logger.warning("RC柱断面タイプが未対応です: Section ID %s", sec_id)

    def _extract_cft_column_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """CFT構造柱断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_cft_elem in sections_element.findall(
            ".//stb:StbSecColumn_CFT", namespaces
        ):
            sec_id = sec_cft_elem.get("id")
            sec_name = sec_cft_elem.get("name")

            if not sec_id:
                continue

            steel_fig = sec_cft_elem.find(
                ".//stb:StbSecSteelFigureColumn_CFT", namespaces
            )

            if steel_fig is None:
                logger.warning(
                    "StbSecSteelFigureColumn_CFT 要素が見つかりません (Section ID %s)",
                    sec_id,
                )
                continue

            # 統一処理を使用してSame/NotSameパターンを処理
            context_info = {
                "sec_id": sec_id,
                "sec_name": sec_name,
                "structure_type": "CFT"
            }
            
            shape_processor = lambda steel_elem, elem: self._process_cft_column_shape(steel_elem, elem, context_info)
            results = self.process_same_notsame_pattern(steel_fig, shape_processor, context_info)
            
            if results:
                # 結果の処理（S柱と同じロジック）
                if len(results) == 1:
                    sections_data[sec_id] = results[0]
                    logger.debug("CFT柱断面を解析: ID=%s", sec_id)
                elif len(results) == 2:
                    bottom_info = next((r for r in results if r.get("position") == "BOTTOM"), None)
                    top_info = next((r for r in results if r.get("position") == "TOP"), None)
                    
                    if bottom_info and top_info:
                        if bottom_info.get("stb_shape_name") == top_info.get("stb_shape_name"):
                            sections_data[sec_id] = bottom_info
                            logger.debug("CFT NotSame柱断面（同じ断面）: ID=%s", sec_id)
                        else:
                            sections_data[sec_id] = {
                                "section_type": "TAPERED_CFT",
                                "start_section": bottom_info,
                                "end_section": top_info,
                                "stb_name": sec_name,
                                "stb_structure_type": "CFT",
                            }
                            logger.debug("CFT NotSame変断面柱: ID=%s", sec_id)
                    elif bottom_info:
                        sections_data[sec_id] = bottom_info
                        logger.debug("CFT NotSame柱断面（下端のみ）: ID=%s", sec_id)
                    elif top_info:
                        sections_data[sec_id] = top_info
                        logger.debug("CFT NotSame柱断面（上端のみ）: ID=%s", sec_id)
                continue

            logger.warning("CFT柱断面タイプが未対応です: Section ID %s", sec_id)

    def _process_cft_column_shape(self, steel_elem, elem, context_info: Dict) -> Optional[Dict]:
        """CFT構造柱断面の個別形状処理"""
        try:
            sec_dict = self._extract_steel_section_dict(steel_elem)
            if sec_dict:
                sec_dict["stb_name"] = context_info["sec_name"]
                sec_dict["stb_shape_name"] = elem.get("shape")
                sec_dict["stb_structure_type"] = context_info["structure_type"]
                # CFTの場合はstrengthも追加
                strength = elem.get("strength")
                if strength:
                    sec_dict["strength_main"] = strength
                return sec_dict
            return None
        except Exception as e:
            logger.error("CFT構造柱断面形状処理エラー: %s", e)
            return None

    def _extract_src_column_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """SRC構造柱断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_src_elem in sections_element.findall(
            ".//stb:StbSecColumn_SRC", namespaces
        ):
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
                    "rebar_section": rebar_info,
                }

                sections_data[sec_id] = src_section_info
                logger.debug(
                    "SRC柱断面 ID %s を解析しました: RC=%s, Steel=%s",
                    sec_id,
                    rc_info.get("section_type"),
                    steel_info.get("section_type"),
                )
            else:
                logger.warning("SRC柱断面 ID %s の構成要素が不完全です", sec_id)

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
                    "material_type": "RC",
                }

        # 円形断面
        circle_elem = rc_fig.find("stb:StbSecColumn_SRC_Circle", namespaces)
        if circle_elem is not None:
            diameter = self._float_attr(circle_elem, "D")

            if diameter:
                return {
                    "section_type": "CIRCLE",
                    "radius": diameter / 2.0,
                    "material_type": "RC",
                }

        logger.warning("対応するSRC RC断面形状が見つかりません")
        return None

    def _extract_src_steel_section(self, src_elem, namespaces) -> Optional[Dict]:
        """SRC柱の鋼材断面部分を抽出"""
        steel_fig = src_elem.find(".//stb:StbSecSteelFigureColumn_SRC", namespaces)
        if steel_fig is None:
            logger.warning("StbSecSteelFigureColumn_SRC が見つかりません")
            return None

        # Same構成の処理
        same_elem = steel_fig.find("stb:StbSecSteelColumn_SRC_Same", namespaces)
        if same_elem is not None:
            return self._extract_src_same_steel_section(same_elem, namespaces)

        logger.warning("SRC NotSame構成は現在未対応です")
        return None

    def _extract_src_same_steel_section(self, same_elem, namespaces) -> Optional[Dict]:
        """SRC Same構成の鋼材断面を抽出"""

        # BOX断面
        box_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeBox", namespaces)
        if box_elem is not None:
            shape_name = box_elem.get("shape")
            encase_type = box_elem.get("encase_type", "ENCASEDANDINFILLED")
            strength = box_elem.get("strength", "BCR295")

            if shape_name:
                steel_elem = self.find_steel_section_by_name(None, shape_name)
                if steel_elem is not None:
                    # BOX断面の処理（Roll-BOXとBuild-BOXの両方に対応）
                    if self._is_tag(steel_elem, "StbSecRoll-BOX"):
                        box_info = self.extract_box_steel_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
                        box_info = self.extract_build_box_section(steel_elem)
                    else:
                        logger.warning("BOX断面の種類が不明: %s", steel_elem.tag)
                        box_info = None

                    if box_info:
                        box_info["encase_type"] = encase_type
                        box_info["strength_main"] = strength
                        box_info["steel_shape_name"] = shape_name
                        return box_info
                else:
                    logger.warning("BOX断面の鋼材要素が見つかりません: %s", shape_name)

        # PIPE断面
        pipe_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapePipe", namespaces)
        if pipe_elem is not None:
            shape_name = pipe_elem.get("shape")
            encase_type = pipe_elem.get("encase_type", "ENCASEDANDINFILLED")
            strength = pipe_elem.get("strength", "SN400B")

            if shape_name:
                steel_elem = self.find_steel_section_by_name(None, shape_name)
                if steel_elem is not None:
                    pipe_info = self.extract_pipe_steel_section(steel_elem)
                    if pipe_info:
                        pipe_info["encase_type"] = encase_type
                        pipe_info["strength_main"] = strength
                        pipe_info["steel_shape_name"] = shape_name
                        return pipe_info

        # Cross断面（クロス配置）
        cross_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeCross", namespaces)
        if cross_elem is not None:
            return self._extract_src_cross_section(cross_elem)

        # T断面（十字配置）
        t_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeT", namespaces)
        if t_elem is not None:
            return self._extract_src_t_section(t_elem)

        # H断面（単一）
        h_elem = same_elem.find("stb:StbSecColumn_SRC_SameShapeH", namespaces)
        if h_elem is not None:
            shape_name = h_elem.get("shape")
            strength_main = h_elem.get("strength_main", "SN400B")

            if shape_name:
                steel_elem = self.find_steel_section_by_name(None, shape_name)
                if steel_elem is not None:
                    h_info = self.extract_h_steel_section(steel_elem)
                    if h_info:
                        h_info["strength_main"] = strength_main
                        h_info["steel_shape_name"] = shape_name
                        return h_info
                else:
                    logger.warning("H断面の鋼材要素が見つかりません: %s", shape_name)

        logger.warning("対応するSRC鋼材断面形状が見つかりません")
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

        if h_steel_elem is None:
            logger.warning("T断面のH鋼材要素が見つかりません: %s", shape_h)
            
        if t_steel_elem is None:
            logger.warning("T断面のT鋼材要素が見つかりません: %s", shape_t)

        if h_steel_elem is None or t_steel_elem is None:
            logger.warning(
                "T断面の鋼材要素が見つかりません: H=%s, T=%s", shape_h, shape_t
            )
            return None

        h_info = self.extract_h_steel_section(h_steel_elem)
        t_info = self.extract_h_steel_section(t_steel_elem)

        if h_info and t_info:
            return {
                "section_type": "T_COMPOSITE",
                "direction_type": direction_type,
                "h_section": {
                    **h_info,
                    "steel_shape_name": shape_h,
                    "strength_main": strength_h,
                },
                "t_section": {
                    **t_info,
                    "steel_shape_name": shape_t,
                    "strength_main": strength_t,
                },
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
                "n_band_direction_y": self._float_attr(bar_elem, "N_band_direction_Y"),
            }

        return None

    def _extract_steel_section_dict(self, steel_elem):
        """鋼材断面要素から断面辞書を抽出"""
        if self._is_tag(steel_elem, "StbSecBuild-H"):
            return self.extract_build_h_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-H"):
            return self.extract_h_steel_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-BOX"):
            return self.extract_box_steel_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
            return self.extract_build_box_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecPipe"):
            return self.extract_pipe_steel_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-C"):
            return self.extract_c_steel_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-L"):
            return self._extract_l_section_params(steel_elem)
        elif self._is_tag(steel_elem, "StbSecLipC"):
            return self.extract_lip_c_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecFlatBar"):
            return self.extract_flat_bar_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoundBar"):
            return self.extract_round_bar_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecFiveTypes"):
            return self.extract_five_types_section(steel_elem)
        else:
            logger.warning("未対応の鋼材断面形状: %s", steel_elem.tag)
            return None

    def _extract_src_cross_section(self, cross_elem) -> Optional[Dict]:
        """SRC Cross断面（クロス配置）を抽出"""
        direction_type = cross_elem.get("direction_type")
        # Cross断面ではshape_Xとshape_Yが使用される
        shape_x = cross_elem.get("shape_X")
        shape_y = cross_elem.get("shape_Y") 
        strength_x = cross_elem.get("strength_main_X", "SN400B")
        strength_y = cross_elem.get("strength_main_Y", "SN400B")
        
        if not (shape_x and shape_y):
            logger.warning("Cross断面のshape_Xまたはshape_Yが不足しています")
            return None

        # H断面要素を取得
        x_steel_elem = self.find_steel_section_by_name(None, shape_x)
        y_steel_elem = self.find_steel_section_by_name(None, shape_y)
        
        if x_steel_elem is None:
            logger.warning("Cross断面のX鋼材要素が見つかりません: %s", shape_x)
            
        if y_steel_elem is None:
            logger.warning("Cross断面のY鋼材要素が見つかりません: %s", shape_y)

        if x_steel_elem is None or y_steel_elem is None:
            logger.warning("Cross断面の鋼材要素が見つかりません: X=%s, Y=%s", shape_x, shape_y)
            return None

        x_info = self.extract_h_steel_section(x_steel_elem)
        y_info = self.extract_h_steel_section(y_steel_elem)
        
        if x_info and y_info:
            return {
                "section_type": "CROSS_COMPOSITE",
                "direction_type": direction_type,
                "x_section": {**x_info, "steel_shape_name": shape_x, "strength_main": strength_x},
                "y_section": {**y_info, "steel_shape_name": shape_y, "strength_main": strength_y}
            }
        
        return None

    def _is_tag(self, element, tag_name: str) -> bool:
        """要素のタグ名をチェック"""
        if element is None:
            return False
        return element.tag.endswith(tag_name)
