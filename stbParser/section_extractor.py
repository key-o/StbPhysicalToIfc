# section_extractor.py
from typing import Dict, Optional
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger


logger = get_logger(__name__)


class SectionExtractor(BaseSectionExtractor):
    """ST-Bridge断面情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        """ST-Bridgeから断面情報を抽出

        Returns:
            断面辞書 {section_id: section_info}
        """
        sections_data = {}

        stb_sections_element = self.find_element(".//stb:StbSections")
        if stb_sections_element is None:
            logger.warning("StbSections 要素が見つかりません")
            return sections_data

        # RC柱断面の処理
        self._extract_rc_sections(stb_sections_element, sections_data)

        # 鋼材柱断面の処理
        self._extract_steel_sections(stb_sections_element, sections_data)

        # S柱断面の処理（新規追加）
        self._extract_s_column_sections(stb_sections_element, sections_data)

        # CFT柱断面の処理（今回追加）
        self._extract_cft_column_sections(stb_sections_element, sections_data)

        # S梁断面の処理（今回追加）
        self._extract_s_beam_sections(stb_sections_element, sections_data)

        # RC梁断面の処理（今回追加）
        self._extract_rc_beam_sections(stb_sections_element, sections_data)

        return sections_data

    def _extract_rc_sections(self, sections_element, sections_data: Dict[str, Dict]):
        """RC柱断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_rc_elem in sections_element.findall(
            ".//stb:StbSecColumn_RC", namespaces
        ):
            sec_id = sec_rc_elem.get("id")
            sec_name = sec_rc_elem.get("name")

            if not sec_id:
                continue

            # 矩形断面の処理
            rect_section = self._extract_rc_rect_section(sec_rc_elem, sec_name)
            if rect_section:
                sections_data[sec_id] = rect_section
                continue

            # 円形断面の処理
            circle_section = self._extract_rc_circle_section(sec_rc_elem, sec_name)
            if circle_section:
                sections_data[sec_id] = circle_section
                continue

            logger.warning("RC柱断面タイプが未対応です: Section ID %s", sec_id)

    def _extract_rc_rect_section(self, sec_rc_elem, sec_name: str) -> Optional[Dict]:
        """RC矩形断面の抽出"""
        namespaces = self.get_namespaces()

        rect_figure = sec_rc_elem.find(
            ".//stb:StbSecFigureColumn_RC/stb:StbSecColumn_RC_Rect", namespaces
        )

        if rect_figure is None:
            return None

        try:
            width_x = float(rect_figure.get("width_X"))
            width_y = float(rect_figure.get("width_Y"))
            return {
                "section_type": "RECTANGLE",
                "width_x": width_x,
                "width_y": width_y,
                "stb_name": sec_name,
            }
        except (TypeError, ValueError) as e:
            sec_id = sec_rc_elem.get("id")
            logger.warning(
                "RC柱矩形断面の寸法を解析できません (ID: %s): %s",
                sec_id,
                e,
            )
            return None

    def _extract_rc_circle_section(self, sec_rc_elem, sec_name: str) -> Optional[Dict]:
        """RC円形断面の抽出"""
        namespaces = self.get_namespaces()

        circle_figure = sec_rc_elem.find(
            ".//stb:StbSecFigureColumn_RC/stb:StbSecColumn_RC_Circle", namespaces
        )

        if circle_figure is None:
            return None

        try:
            # ST-Bridgeでは'D'属性が直径を表す
            diameter = float(circle_figure.get("D"))
            radius = diameter / 2.0  # 直径から半径に変換
            sec_id = sec_rc_elem.get("id")
            logger.debug(
                "RC円形柱断面を解析: ID=%s, 直径=%smm, 半径=%smm",
                sec_id,
                diameter,
                radius,
            )
            return {
                "section_type": "CIRCLE",
                "radius": radius,
                "stb_name": sec_name,
            }
        except (TypeError, ValueError) as e:
            sec_id = sec_rc_elem.get("id")
            logger.warning(
                "RC柱円形断面の直径を解析できません (ID: %s): %s",
                sec_id,
                e,
            )
            return None

    def _extract_steel_sections(self, sections_element, sections_data: Dict[str, Dict]):
        """鋼材柱断面の抽出"""
        namespaces = self.get_namespaces()

        stb_sec_steel_element = sections_element.find(".//stb:StbSecSteel", namespaces)
        if stb_sec_steel_element is None:
            return

        # H形鋼断面の処理
        for h_steel_elem in stb_sec_steel_element.findall(
            "stb:StbSecRoll-H", namespaces
        ):
            h_section = self.extract_h_steel_section(h_steel_elem)
            if h_section:
                sec_id = h_steel_elem.get("id")
                if sec_id:
                    sections_data[sec_id] = h_section

        # Build-H形鋼断面の処理
        for bh_elem in stb_sec_steel_element.findall("stb:StbSecBuild-H", namespaces):
            bh_section = self.extract_build_h_section(bh_elem)
            if bh_section:
                sec_id = bh_elem.get("id")
                if sec_id:
                    sections_data[sec_id] = bh_section

        # BOX形鋼断面の処理
        for box_steel_elem in stb_sec_steel_element.findall(
            "stb:StbSecRoll-BOX", namespaces
        ):
            box_section = self.extract_box_steel_section(box_steel_elem)
            if box_section:
                sec_id = box_steel_elem.get("id")
                if sec_id:
                    sections_data[sec_id] = box_section

        # 未定義断面の警告処理
        for undef_elem in stb_sec_steel_element.findall(
            "stb:StbSecUndefined", namespaces
        ):
            sec_id = undef_elem.get("id")
            logger.warning("Section ID %s は未定義断面のためスキップします", sec_id)

        # L形鋼断面の処理
        for l_elem in stb_sec_steel_element.findall("stb:StbSecRoll-L", namespaces):
            l_section = self._extract_l_section_params(l_elem)
            if l_section:
                sec_id = l_elem.get("id")
                if sec_id:
                    sections_data[sec_id] = l_section

        # フラットバー断面の処理
        for fb_elem in stb_sec_steel_element.findall("stb:StbSecFlatBar", namespaces):
            fb_section = self.extract_flat_bar_section(fb_elem)
            if fb_section:
                sec_id = fb_elem.get("id")
                if sec_id:
                    sections_data[sec_id] = fb_section

    def _extract_h_steel_section(self, h_steel_elem) -> Optional[Dict]:
        """H形鋼断面の抽出"""
        sec_name = h_steel_elem.get("name")

        try:
            A = float(h_steel_elem.get("A"))  # 全高
            B = float(h_steel_elem.get("B"))  # 全幅
            t1 = float(h_steel_elem.get("t1"))  # ウェブ厚
            t2 = float(h_steel_elem.get("t2"))  # フランジ厚
            r = (
                float(h_steel_elem.get("r")) if h_steel_elem.get("r") else None
            )  # フィレット半径

            return {
                "section_type": "H",
                "overall_depth": A,
                "overall_width": B,
                "web_thickness": t1,
                "flange_thickness": t2,
                "fillet_radius": r,
                "stb_name": sec_name,
            }
        except (TypeError, ValueError) as e:
            sec_id = h_steel_elem.get("id")
            logger.warning(
                "H形鋼断面のパラメータを解析できません (ID: %s): %s",
                sec_id,
                e,
            )
            return None

    def _extract_s_column_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """S柱断面の抽出（shape名からStbSecSteelの情報を参照）"""
        namespaces = self.get_namespaces()

        # StbSecColumn_S要素を検索
        for sec_s_elem in sections_element.findall(".//stb:StbSecColumn_S", namespaces):
            sec_id = sec_s_elem.get("id")
            sec_name = sec_s_elem.get("name")

            # isReferenceDirection属性を取得（デフォルトはfalse）
            is_reference_direction = (
                sec_s_elem.get("isReferenceDirection", "false").lower() == "true"
            )

            if not sec_id:
                continue

            steel_fig = sec_s_elem.find(
                ".//stb:StbSecSteelFigureColumn_S",
                namespaces,
            )

            if steel_fig is None:
                logger.warning(
                    "StbSecSteelFigureColumn_S 要素が見つかりません (Section ID %s)",
                    sec_id,
                )
                continue

            steel_same_elem = steel_fig.find(
                "stb:StbSecSteelColumn_S_Same",
                namespaces,
            )
            not_same_elems = steel_fig.findall(
                "stb:StbSecSteelColumn_S_NotSame",
                namespaces,
            )

            if steel_same_elem is not None:
                shape_name = steel_same_elem.get("shape")
                strength_main = steel_same_elem.get("strength_main")
                if not shape_name:
                    logger.warning(
                        "S柱断面ID %s にshape属性がありません",
                        sec_id,
                    )
                    continue
                # steel element を検索
                steel_elem = self.find_steel_section_by_name(
                    sections_element, shape_name
                )
                if steel_elem is None:
                    logger.warning(
                        "shape '%s' の鋼材断面要素が見つかりません (Section ID %s)",
                        shape_name,
                        sec_id,
                    )
                    continue
                # element から断面 dict を抽出
                if self._is_tag(steel_elem, "StbSecBuild-H"):
                    sec_dict = self.extract_build_h_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-H"):
                    sec_dict = self.extract_h_steel_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecPipe"):
                    sec_dict = self.extract_pipe_steel_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoundBar"):
                    sec_dict = self.extract_round_bar_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
                    sec_dict = self.extract_build_box_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-BOX"):
                    sec_dict = self.extract_box_steel_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-C"):
                    sec_dict = self._extract_c_section_params(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-L"):
                    sec_dict = self._extract_l_section_params(steel_elem)
                elif "LipC" in steel_elem.tag:
                    sec_dict = self.extract_lip_c_section(steel_elem)
                else:
                    sec_dict = None
                if sec_dict:
                    sec_dict["strength_main"] = strength_main
                    sec_dict["stb_name"] = sec_name
                    sec_dict["stb_shape_name"] = shape_name
                    sec_dict["is_reference_direction"] = is_reference_direction
                    sections_data[sec_id] = sec_dict
                    logger.debug(
                        "S柱断面を解析: ID=%s, shape=%s, strength=%s, isRefDir=%s",
                        sec_id,
                        shape_name,
                        strength_main,
                        is_reference_direction,
                    )
                else:
                    logger.warning(
                        "shape '%s' の鋼材断面情報を取得できません (Section ID %s)",
                        shape_name,
                        sec_id,
                    )
            elif not_same_elems:
                top_info = None
                bottom_info = None
                for ns_elem in not_same_elems:
                    pos = ns_elem.get("pos")
                    shape_name = ns_elem.get("shape")
                    strength_main = ns_elem.get("strength_main")
                    if not pos or not shape_name:
                        logger.warning(
                            "StbSecSteelColumn_S_NotSame の属性が不足しています (Section ID %s)",
                            sec_id,
                        )
                        continue
                    steel_elem = self.find_steel_section_by_name(
                        sections_element,
                        shape_name,
                    )
                    if steel_elem is None:
                        logger.warning(
                            "shape '%s' の鋼材断面要素が見つかりません (Section ID %s)",
                            shape_name,
                            sec_id,
                        )
                        continue
                    if self._is_tag(steel_elem, "StbSecBuild-H"):
                        sec_dict = self.extract_build_h_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-H"):
                        sec_dict = self.extract_h_steel_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecPipe"):
                        sec_dict = self.extract_pipe_steel_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoundBar"):
                        sec_dict = self.extract_round_bar_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
                        sec_dict = self.extract_build_box_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-BOX"):
                        sec_dict = self.extract_box_steel_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-C"):
                        sec_dict = self._extract_c_section_params(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-L"):
                        sec_dict = self._extract_l_section_params(steel_elem)
                    elif "LipC" in steel_elem.tag:
                        sec_dict = self.extract_lip_c_section(steel_elem)
                    else:
                        sec_dict = None

                    if sec_dict:
                        sec_dict["strength_main"] = strength_main
                        sec_dict["stb_name"] = sec_name
                        sec_dict["stb_shape_name"] = shape_name
                        if pos == "BOTTOM":
                            bottom_info = sec_dict
                        elif pos == "TOP":
                            top_info = sec_dict
                    else:
                        logger.warning(
                            "shape '%s' の鋼材断面情報を取得できません (Section ID %s)",
                            shape_name,
                            sec_id,
                        )
                if bottom_info and top_info:
                    sections_data[sec_id] = {
                        "section_type": "TAPERED_S",
                        "start_section": bottom_info,
                        "end_section": top_info,
                        "stb_name": sec_name,
                    }
                    logger.debug(
                        "変断面S柱を解析: ID=%s, bottom=%s, top=%s",
                        sec_id,
                        bottom_info.get("stb_shape_name"),
                        top_info.get("stb_shape_name"),
                    )
                else:
                    logger.warning(
                        "StbSecSteelColumn_S_NotSame の定義が不完全です (Section ID %s)",
                        sec_id,
                    )
            else:
                logger.warning(
                    "StbSecSteelColumn_S_Same 要素が見つかりません (Section ID %s)",
                    sec_id,
                )

    def _extract_cft_column_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """CFT柱断面の抽出（shape名からStbSecSteelの情報を参照）"""
        namespaces = self.get_namespaces()

        for sec_elem in sections_element.findall(".//stb:StbSecColumn_CFT", namespaces):
            sec_id = sec_elem.get("id")
            sec_name = sec_elem.get("name")

            if not sec_id:
                continue

            steel_fig = sec_elem.find(".//stb:StbSecSteelFigureColumn_CFT", namespaces)

            if steel_fig is None:
                logger.warning(
                    "StbSecSteelFigureColumn_CFT 要素が見つかりません (Section ID %s)",
                    sec_id,
                )
                continue

            same_elem = steel_fig.find("stb:StbSecSteelColumn_CFT_Same", namespaces)
            not_same_elems = steel_fig.findall(
                "stb:StbSecSteelColumn_CFT_NotSame", namespaces
            )
            if same_elem is not None:
                shape_name = same_elem.get("shape")
                strength = same_elem.get("strength")
                if not shape_name:
                    logger.warning("CFT柱断面ID %s にshape属性がありません", sec_id)
                    continue
                steel_elem = self.find_steel_section_by_name(
                    sections_element, shape_name
                )
                if steel_elem is None:
                    logger.warning(
                        "shape '%s' の鋼材断面要素が見つかりません (Section ID %s)",
                        shape_name,
                        sec_id,
                    )
                    continue
                if self._is_tag(steel_elem, "StbSecBuild-H"):
                    sec_dict = self.extract_build_h_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-H"):
                    sec_dict = self.extract_h_steel_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecPipe"):
                    sec_dict = self.extract_pipe_steel_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoundBar"):
                    sec_dict = self.extract_round_bar_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
                    sec_dict = self.extract_build_box_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-BOX"):
                    sec_dict = self.extract_box_steel_section(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-C"):
                    sec_dict = self._extract_c_section_params(steel_elem)
                elif self._is_tag(steel_elem, "StbSecRoll-L"):
                    sec_dict = self._extract_l_section_params(steel_elem)
                elif "LipC" in steel_elem.tag:
                    sec_dict = self.extract_lip_c_section(steel_elem)
                else:
                    sec_dict = None
                if sec_dict:
                    sec_dict["strength_main"] = strength
                    sec_dict["stb_name"] = sec_name
                    sec_dict["stb_shape_name"] = shape_name
                    sections_data[sec_id] = sec_dict
                    logger.debug(
                        "CFT柱断面を解析: ID=%s, shape=%s, strength=%s",
                        sec_id,
                        shape_name,
                        strength,
                    )
                else:
                    logger.warning(
                        "shape '%s' の鋼材断面情報を取得できません (Section ID %s)",
                        shape_name,
                        sec_id,
                    )
            elif not_same_elems:
                bottom_info = None
                top_info = None
                for ns_elem in not_same_elems:
                    pos = ns_elem.get("pos")
                    shape_name = ns_elem.get("shape")
                    strength = ns_elem.get("strength")
                    if not pos or not shape_name:
                        logger.warning(
                            "StbSecSteelColumn_CFT_NotSame の属性が不足しています (Section ID %s)",
                            sec_id,
                        )
                        continue
                    steel_elem = self.find_steel_section_by_name(
                        sections_element, shape_name
                    )
                    if steel_elem is None:
                        logger.warning(
                            "shape '%s' の鋼材断面要素が見つかりません (Section ID %s)",
                            shape_name,
                            sec_id,
                        )
                        continue
                    if self._is_tag(steel_elem, "StbSecBuild-H"):
                        sec_dict = self.extract_build_h_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-H"):
                        sec_dict = self.extract_h_steel_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecPipe"):
                        sec_dict = self.extract_pipe_steel_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
                        sec_dict = self.extract_build_box_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-BOX"):
                        sec_dict = self.extract_box_steel_section(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-C"):
                        sec_dict = self._extract_c_section_params(steel_elem)
                    elif self._is_tag(steel_elem, "StbSecRoll-L"):
                        sec_dict = self._extract_l_section_params(steel_elem)
                    elif "LipC" in steel_elem.tag:
                        sec_dict = self.extract_lip_c_section(steel_elem)
                    else:
                        sec_dict = None

                    if sec_dict:
                        sec_dict["strength_main"] = strength
                        sec_dict["stb_name"] = sec_name
                        sec_dict["stb_shape_name"] = shape_name
                        if pos == "BOTTOM":
                            bottom_info = sec_dict
                        elif pos == "TOP":
                            top_info = sec_dict
                    else:
                        logger.warning(
                            "shape '%s' の鋼材断面情報を取得できません (Section ID %s)",
                            shape_name,
                            sec_id,
                        )

                if bottom_info and top_info:
                    sections_data[sec_id] = {
                        "section_type": "TAPERED_CFT",
                        "start_section": bottom_info,
                        "end_section": top_info,
                        "stb_name": sec_name,
                    }
                    logger.debug(
                        "変断面CFT柱を解析: ID=%s, bottom=%s, top=%s",
                        sec_id,
                        bottom_info.get("stb_shape_name"),
                        top_info.get("stb_shape_name"),
                    )
                else:
                    logger.warning(
                        "StbSecSteelColumn_CFT_NotSame の定義が不完全です (Section ID %s)",
                        sec_id,
                    )
            else:
                logger.warning(
                    "StbSecSteelColumn_CFT_Same 要素が見つかりません (Section ID %s)",
                    sec_id,
                )

    def _extract_s_beam_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """S梁断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_elem in sections_element.findall(".//stb:StbSecBeam_S", namespaces):
            sec_id = sec_elem.get("id")
            sec_name = sec_elem.get("name")

            if not sec_id:
                continue

            steel_fig = sec_elem.find(".//stb:StbSecSteelFigureBeam_S", namespaces)

            if steel_fig is None:
                logger.warning(
                    "StbSecSteelFigureBeam_S 要素が見つかりません (Section ID %s)",
                    sec_id,
                )
                continue

            # 等断面梁の処理
            straight_elem = steel_fig.find("stb:StbSecSteelBeam_S_Straight", namespaces)
            if straight_elem is not None:
                shape_name = straight_elem.get("shape")
                strength_main = straight_elem.get("strength_main")
                if not shape_name:
                    logger.warning("S梁断面ID %s にshape属性がありません", sec_id)
                    continue

                steel_elem = self.find_steel_section_by_name(
                    sections_element, shape_name
                )
                if steel_elem is None:
                    logger.warning(
                        "shape '%s' の鋼材断面要素が見つかりません (Section ID %s)",
                        shape_name,
                        sec_id,
                    )
                    continue

                sec_dict = self._extract_steel_section_dict(steel_elem)
                if sec_dict:
                    sec_dict["strength_main"] = strength_main
                    sec_dict["stb_name"] = sec_name
                    sec_dict["stb_shape_name"] = shape_name
                    sections_data[sec_id] = sec_dict
                    logger.debug(
                        "S梁断面を解析: ID=%s, shape=%s, strength=%s",
                        sec_id,
                        shape_name,
                        strength_main,
                    )
                else:
                    logger.warning(
                        "shape '%s' の鋼材断面情報を取得できません (Section ID %s)",
                        shape_name,
                        sec_id,
                    )
                continue

            # 接合部タイプ梁の処理
            joint_elems = steel_fig.findall("stb:StbSecSteelBeam_S_Joint", namespaces)
            if joint_elems:
                # 接合部タイプの場合、CENTER位置の断面を代表断面として使用
                center_elem = None
                for joint_elem in joint_elems:
                    pos = joint_elem.get("pos")
                    if pos == "CENTER":
                        center_elem = joint_elem
                        break

                # CENTER断面がない場合は最初の要素を使用
                if center_elem is None and joint_elems:
                    center_elem = joint_elems[0]

                if center_elem is not None:
                    shape_name = center_elem.get("shape")
                    strength_main = center_elem.get("strength_main")
                    if not shape_name:
                        logger.warning("S梁断面ID %s にshape属性がありません", sec_id)
                        continue

                    steel_elem = self.find_steel_section_by_name(
                        sections_element, shape_name
                    )
                    if steel_elem is None:
                        logger.warning(
                            "shape '%s' の鋼材断面要素が見つかりません (Section ID %s)",
                            shape_name,
                            sec_id,
                        )
                        continue

                    sec_dict = self._extract_steel_section_dict(steel_elem)
                    if sec_dict:
                        sec_dict["strength_main"] = strength_main
                        sec_dict["stb_name"] = sec_name
                        sec_dict["stb_shape_name"] = shape_name
                        sections_data[sec_id] = sec_dict
                        logger.debug(
                            "S梁断面(接合部タイプ)を解析: ID=%s, shape=%s, strength=%s",
                            sec_id,
                            shape_name,
                            strength_main,
                        )
                    else:
                        logger.warning(
                            "shape '%s' の鋼材断面情報を取得できません (Section ID %s)",
                            shape_name,
                            sec_id,
                        )
                continue

            # 変断面梁の処理
            haunch_elem = steel_fig.find("stb:StbSecSteelBeam_S_Haunch", namespaces)
            if haunch_elem is not None:
                # ハンチ梁の処理（必要に応じて実装）
                logger.debug("ハンチ梁断面 ID %s は現在対応していません", sec_id)
                continue

            logger.warning("S梁断面タイプが未対応です: Section ID %s", sec_id)

    def _extract_steel_section_dict(self, steel_elem):
        """鋼材断面要素から断面辞書を抽出"""
        if self._is_tag(steel_elem, "StbSecBuild-H"):
            return self.extract_build_h_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-H"):
            return self.extract_h_steel_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecPipe"):
            return self.extract_pipe_steel_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoundBar"):
            return self.extract_round_bar_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
            return self.extract_build_box_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-BOX"):
            return self.extract_box_steel_section(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-C"):
            return self._extract_c_section_params(steel_elem)
        elif self._is_tag(steel_elem, "StbSecRoll-L"):
            return self._extract_l_section_params(steel_elem)
        elif "LipC" in steel_elem.tag:
            return self.extract_lip_c_section(steel_elem)
        else:
            return None

    def _extract_rc_beam_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """RC梁断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_elem in sections_element.findall(".//stb:StbSecBeam_RC", namespaces):
            sec_id = sec_elem.get("id")
            sec_name = sec_elem.get("name")

            if not sec_id:
                continue

            # RC矩形断面の処理
            rect_section = self._extract_rc_beam_rect_section(sec_elem, sec_name)
            if rect_section:
                sections_data[sec_id] = rect_section
                logger.debug(
                    "RC梁断面を解析: ID=%s, name=%s, type=RECTANGLE",
                    sec_id,
                    sec_name,
                )
                continue

            logger.warning("RC梁断面タイプが未対応です: Section ID %s", sec_id)

    def _extract_rc_beam_rect_section(self, sec_rc_elem, sec_name: str):
        """RC梁矩形断面の抽出"""
        namespaces = self.get_namespaces()

        # StbSecBeam_RC_Rectを確認
        rect_figure = sec_rc_elem.find(
            ".//stb:StbSecFigureBeam_RC/stb:StbSecBeam_RC_Rect", namespaces
        )

        if rect_figure is not None:
            try:
                width = float(rect_figure.get("width"))
                height = float(rect_figure.get("height"))
                return {
                    "section_type": "RECTANGLE",
                    "width": width,
                    "height": height,
                    "stb_name": sec_name,
                }
            except (TypeError, ValueError) as e:
                sec_id = sec_rc_elem.get("id")
                logger.warning(
                    "RC梁矩形断面の寸法を解析できません (ID: %s): %s",
                    sec_id,
                    e,
                )
                return None

        # StbSecBeam_RC_Straightを確認
        straight_figure = sec_rc_elem.find(
            ".//stb:StbSecFigureBeam_RC/stb:StbSecBeam_RC_Straight", namespaces
        )

        if straight_figure is not None:
            try:
                width = float(straight_figure.get("width"))
                depth = float(straight_figure.get("depth"))
                return {
                    "section_type": "RECTANGLE",
                    "width": width,
                    "height": depth,
                    "stb_name": sec_name,
                }
            except (TypeError, ValueError) as e:
                sec_id = sec_rc_elem.get("id")
                logger.warning(
                    "RC梁ストレート断面の寸法を解析できません (ID: %s): %s",
                    sec_id,
                    e,
                )
                return None

        return None
