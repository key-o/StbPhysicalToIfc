# beam_section_extractor.py
from typing import Dict, Optional
from .xml_parser import STBXMLParser
from .section_extractor_base import BaseSectionExtractor
from utils.logger import get_logger


logger = get_logger(__name__)


class BeamSectionExtractor(BaseSectionExtractor):
    """ST-Bridge梁断面情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_sections(self) -> Dict[str, Dict]:
        """ST-Bridgeから梁断面情報を抽出

        Returns:
            断面辞書 {section_id: section_info}
        """
        sections_data = {}

        stb_sections_element = self.find_element(".//stb:StbSections")
        if stb_sections_element is None:
            logger.warning("StbSections element not found.")
            return sections_data

        # 鋼構造梁断面の処理
        self._extract_steel_beam_sections(stb_sections_element, sections_data)

        # RC構造梁断面の処理
        self._extract_rc_beam_sections(stb_sections_element, sections_data)

        return sections_data

    def _extract_steel_beam_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """鋼構造梁断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_s_elem in sections_element.findall(".//stb:StbSecBeam_S", namespaces):
            sec_id = sec_s_elem.get("id")
            sec_name = sec_s_elem.get("name")

            if not sec_id:
                continue

            # ハンチ付き梁・ジョイント梁またはFiveTypes梁の確認
            haunch_elements = sec_s_elem.findall(
                ".//stb:StbSecSteelFigureBeam_S/stb:StbSecSteelBeam_S_Haunch",
                namespaces,
            )
            five_type_elements = sec_s_elem.findall(
                ".//stb:StbSecSteelFigureBeam_S/stb:StbSecSteelBeam_S_FiveTypes",
                namespaces,
            )
            joint_elements = sec_s_elem.findall(
                ".//stb:StbSecSteelFigureBeam_S/stb:StbSecSteelBeam_S_Joint",
                namespaces,
            )
            taper_elements = sec_s_elem.findall(
                ".//stb:StbSecSteelFigureBeam_S/stb:StbSecSteelBeam_S_Taper",
                namespaces,
            )

            if haunch_elements:
                # ハンチ付き梁の処理
                logger.debug("Found haunched beam section ID %s", sec_id)
                haunch_sections = self._extract_haunch_sections(
                    sections_element, haunch_elements, sec_name
                )
                if haunch_sections:
                    sections_data[sec_id] = {
                        "section_type": "HAUNCH",
                        "haunch_sections": haunch_sections,
                        "stb_name": sec_name,
                    }
                    logger.debug(
                        "Successfully parsed haunched beam section ID %s", sec_id
                    )
            elif five_type_elements:
                # FiveTypes 梁の処理
                logger.debug("Found five-type beam section ID %s", sec_id)
                five_sections = self._extract_five_type_sections(
                    sections_element, five_type_elements, sec_name
                )
                if five_sections:
                    section_type = (
                        "HAUNCH_FIVE"
                        if "HAUNCH_S" in five_sections or "HAUNCH_E" in five_sections
                        else "HAUNCH"
                    )
                    sections_data[sec_id] = {
                        "section_type": section_type,
                        "haunch_sections": five_sections,
                        "stb_name": sec_name,
                    }
                    logger.debug(
                        "Successfully parsed five-type beam section ID %s", sec_id
                    )
            elif joint_elements:
                # ジョイント梁の処理（ハンチ梁と同様に扱う）
                logger.debug("Found joint beam section ID %s", sec_id)
                joint_sections = self._extract_joint_sections(
                    sections_element, joint_elements, sec_name
                )
                if joint_sections:
                    sections_data[sec_id] = {
                        "section_type": "HAUNCH",
                        "haunch_sections": joint_sections,
                        "stb_name": sec_name,
                    }
                    logger.debug("Successfully parsed joint beam section ID %s", sec_id)
            elif taper_elements:
                logger.debug("Found tapered steel beam section ID %s", sec_id)
                taper_info = self._extract_taper_sections(
                    sections_element, taper_elements, sec_name
                )
                if taper_info:
                    sections_data[sec_id] = taper_info
                    logger.debug(
                        "Successfully parsed tapered steel beam section ID %s",
                        sec_id,
                    )
            else:
                # 通常の鋼構造梁の処理 - 共通メソッドを使用
                straight_info = self.find_straight_steel_element(
                    sec_s_elem,
                    ".//stb:StbSecSteelFigureBeam_S/stb:StbSecSteelBeam_S_Straight",
                    namespaces,
                )

                if straight_info is None:
                    logger.warning(
                        "StbSecSteelBeam_S_Straight not found for Section ID %s",
                        sec_id,
                    )
                    continue

                # 共通メソッドを使用して鋼材形状パラメータを取得
                steel_section_info = self.process_steel_shape_params(
                    straight_info["steel_elem"], sec_name
                )

                if steel_section_info:
                    steel_section_info["steel_shape_name"] = straight_info["shape_name"]
                    steel_section_info["stb_name"] = sec_name
                    # 材料情報を設定
                    if straight_info["strength_main"]:
                        steel_section_info["material"] = straight_info["strength_main"]
                    sections_data[sec_id] = steel_section_info
                    logger.debug("鋼構造梁断面ID %s を正常に抽出", sec_id)
                    logger.debug(
                        "鋼材梁断面 ID %s を解析しました: %s",
                        sec_id,
                        straight_info["shape_name"],
                    )
                else:
                    logger.warning(
                        "Section ID %s の鋼材断面パラメータを解析できませんでした",
                        sec_id,
                    )

    def _extract_haunch_sections(
        self, sections_element, haunch_elements, sec_name: str
    ) -> Optional[Dict[str, Dict]]:
        """ハンチ付き梁の各部位の断面情報を抽出"""
        haunch_sections = {}

        for haunch_elem in haunch_elements:
            pos = haunch_elem.get("pos")  # START, CENTER, END
            shape_name = haunch_elem.get("shape")

            if not pos or not shape_name:
                logger.warning("haunch要素にposまたはshapeがありません")
                continue

            logger.debug(
                "Processing haunch position %s with shape: %s", pos, shape_name
            )

            # 形状名からStbSecSteel要素を取得
            steel_elem = self.find_steel_section_by_name(sections_element, shape_name)

            if steel_elem is not None:
                tag = steel_elem.tag
                section_info = None

                if tag.endswith("StbSecRoll-H"):
                    section_info = self.extract_h_steel_section(steel_elem)
                elif tag.endswith("StbSecBuild-H"):
                    section_info = self.extract_build_h_section(steel_elem)
                elif tag.endswith("StbSecRoll-BOX"):
                    section_info = self.extract_box_steel_section(steel_elem)
                elif tag.endswith("StbSecBuild-BOX"):
                    section_info = self.extract_build_box_section(steel_elem)
                elif tag.endswith("StbSecPipe"):
                    section_info = self.extract_pipe_steel_section(steel_elem)
                elif "FlatBar" in tag:
                    section_info = self.extract_flat_bar_section(steel_elem)
                elif tag.endswith("StbSecRoll-C"):
                    section_info = self.extract_c_steel_section(steel_elem)
                elif tag.endswith("StbSecRoll-L"):
                    section_info = self._extract_l_section_params(steel_elem)
                elif tag.endswith("StbSecRoundBar"):
                    section_info = self.extract_round_bar_section(steel_elem)
                elif "LipC" in tag:
                    section_info = self.extract_lip_c_section(steel_elem)
                elif tag.endswith("StbSecFiveTypes"):
                    section_info = self.extract_five_types_section(steel_elem)
                else:
                    logger.warning("ハンチの鋼材形状 '%s' は未サポートです", shape_name)

                if section_info:
                    section_info["steel_shape_name"] = shape_name
                    # ハンチ梁でも断面名（StbSecBeam_Sのname属性）を設定
                    section_info["stb_name"] = sec_name
                    haunch_sections[pos] = section_info
                    logger.debug("ハンチ %s 断面を解析しました: %s", pos, shape_name)
                else:
                    logger.warning(
                        "ハンチ形状 '%s' の鋼材断面データを取得できませんでした",
                        shape_name,
                    )
            else:
                logger.warning(
                    "ハンチ形状 '%s' の鋼材断面要素が見つかりません", shape_name
                )

        return haunch_sections if haunch_sections else None

    def _extract_joint_sections(
        self, sections_element, joint_elements, sec_name: str
    ) -> Optional[Dict[str, Dict]]:
        """ジョイント梁の各部位の断面情報を抽出"""
        joint_sections = {}

        for joint_elem in joint_elements:
            pos = joint_elem.get("pos")
            shape_name = joint_elem.get("shape")

            if not pos or not shape_name:
                logger.warning("joint要素にposまたはshapeがありません")
                continue

            logger.debug("Processing joint position %s with shape: %s", pos, shape_name)

            steel_elem = self.find_steel_section_by_name(sections_element, shape_name)

            if steel_elem is not None:
                tag = steel_elem.tag
                section_info = None

                if tag.endswith("StbSecRoll-H"):
                    section_info = self.extract_h_steel_section(steel_elem)
                elif tag.endswith("StbSecBuild-H"):
                    section_info = self.extract_build_h_section(steel_elem)
                elif tag.endswith("StbSecRoll-BOX"):
                    section_info = self.extract_box_steel_section(steel_elem)
                elif tag.endswith("StbSecBuild-BOX"):
                    section_info = self.extract_build_box_section(steel_elem)
                elif tag.endswith("StbSecPipe"):
                    section_info = self.extract_pipe_steel_section(steel_elem)
                elif "FlatBar" in tag:
                    section_info = self.extract_flat_bar_section(steel_elem)
                elif tag.endswith("StbSecRoll-C"):
                    section_info = self.extract_c_steel_section(steel_elem)
                elif tag.endswith("StbSecRoll-L"):
                    section_info = self._extract_l_section_params(steel_elem)
                elif tag.endswith("StbSecRoundBar"):
                    section_info = self.extract_round_bar_section(steel_elem)
                elif "LipC" in tag:
                    section_info = self.extract_lip_c_section(steel_elem)
                elif tag.endswith("StbSecFiveTypes"):
                    section_info = self.extract_five_types_section(steel_elem)
                else:
                    logger.warning(
                        "ジョイントの鋼材形状 '%s' は未サポートです", shape_name
                    )

                if section_info:
                    section_info["steel_shape_name"] = shape_name
                    # ジョイント梁でも断面名（StbSecBeam_Sのname属性）を設定
                    section_info["stb_name"] = sec_name
                    joint_sections[pos] = section_info
                    logger.debug(
                        "ジョイント %s 断面を解析しました: %s", pos, shape_name
                    )
                else:
                    logger.warning(
                        "ジョイント形状 '%s' の鋼材断面データを取得できませんでした",
                        shape_name,
                    )
            else:
                logger.warning(
                    "ジョイント形状 '%s' の鋼材断面要素が見つかりません", shape_name
                )

        return joint_sections if joint_sections else None

    def _extract_five_type_sections(
        self, sections_element, five_type_elements, sec_name: str
    ) -> Optional[Dict[str, Dict]]:
        """FiveTypes 梁の各部位の断面情報を抽出"""
        five_sections: Dict[str, Dict] = {}

        for ft_elem in five_type_elements:
            pos = ft_elem.get("pos")
            shape_name = ft_elem.get("shape")

            if not pos or not shape_name:
                logger.warning("FiveType要素にposまたはshapeがありません")
                continue

            logger.debug(
                "Processing five type position %s with shape: %s", pos, shape_name
            )

            steel_elem = self.find_steel_section_by_name(sections_element, shape_name)

            if steel_elem is None:
                logger.warning(
                    "FiveType形状 '%s' の鋼材断面データを取得できませんでした",
                    shape_name,
                )
                continue

            tag = steel_elem.tag
            if tag.endswith("StbSecRoll-H") or tag.endswith("StbSecBuild-H"):
                if tag.endswith("StbSecBuild-H"):
                    section_info = self.extract_build_h_section(steel_elem)
                else:
                    section_info = self.extract_h_steel_section(steel_elem)
            elif tag.endswith("StbSecRoll-BOX"):
                section_info = self.extract_box_steel_section(steel_elem)
            elif tag.endswith("StbSecBuild-BOX"):
                section_info = self.extract_build_box_section(steel_elem)
            elif tag.endswith("StbSecPipe"):
                section_info = self.extract_pipe_steel_section(steel_elem)
            elif "FlatBar" in tag:
                section_info = self.extract_flat_bar_section(steel_elem)
            elif tag.endswith("StbSecRoll-C"):
                section_info = self.extract_c_steel_section(steel_elem)
            elif tag.endswith("StbSecRoll-L"):
                section_info = self._extract_l_section_params(steel_elem)
            elif tag.endswith("StbSecRoundBar"):
                section_info = self.extract_round_bar_section(steel_elem)
            elif "LipC" in tag:
                section_info = self.extract_lip_c_section(steel_elem)
            elif tag.endswith("StbSecFiveTypes"):
                section_info = self.extract_five_types_section(steel_elem)
            else:
                logger.warning("FiveTypeの鋼材形状 '%s' は未サポートです", shape_name)
                continue

            if section_info:
                section_info["steel_shape_name"] = shape_name
                # FiveType梁でも断面名（StbSecBeam_Sのname属性）を設定
                section_info["stb_name"] = sec_name
                five_sections[pos] = section_info
                logger.debug("FiveType %s 断面を解析しました: %s", pos, shape_name)
            else:
                logger.warning(
                    "FiveType形状 '%s' の鋼材断面データを取得できませんでした",
                    shape_name,
                )

        if not five_sections:
            return None

        # If only START/CENTER/END are defined, treat as a regular haunch section
        positions = set(five_sections.keys())
        basic = {"START", "CENTER", "END"}
        if positions.issubset(basic):
            return {p: five_sections[p] for p in basic if p in five_sections}

        return five_sections

    def _extract_taper_sections(
        self, sections_element, taper_elements, sec_name: str
    ) -> Optional[Dict]:
        """テーパー鋼梁の開始・終了断面を抽出"""
        start_info = None
        end_info = None

        for taper_elem in taper_elements:
            pos = taper_elem.get("pos")
            shape_name = taper_elem.get("shape")

            if not pos or not shape_name:
                logger.warning("taper要素にposまたはshapeがありません")
                continue

            logger.debug("Processing taper position %s with shape: %s", pos, shape_name)

            steel_elem = self.find_steel_section_by_name(sections_element, shape_name)
            if steel_elem is None:
                logger.warning("形状 '%s' の鋼材断面要素が見つかりません", shape_name)
                continue

            tag = steel_elem.tag
            if tag.endswith("StbSecBuild-H"):
                section_info = self.extract_build_h_section(steel_elem)
            elif tag.endswith("StbSecRoll-H"):
                section_info = self.extract_h_steel_section(steel_elem)
            elif tag.endswith("StbSecRoll-BOX"):
                section_info = self.extract_box_steel_section(steel_elem)
            elif tag.endswith("StbSecBuild-BOX"):
                section_info = self.extract_build_box_section(steel_elem)
            elif "LipC" in tag:
                section_info = self.extract_lip_c_section(steel_elem)
            elif tag.endswith("StbSecRoll-C"):
                section_info = self._extract_c_section_params(steel_elem)
            elif tag.endswith("StbSecRoll-L"):
                section_info = self._extract_l_section_params(steel_elem)
            elif tag.endswith("StbSecPipe"):
                section_info = self.extract_pipe_steel_section(steel_elem)
                if section_info:
                    strength_main = taper_elem.get("strength_main", "SN400B")
                    section_info["profile_type"] = "IfcCircleHollowProfileDef"
                    section_info["material"] = strength_main
            elif tag.endswith("StbSecRoundBar"):
                section_info = self.extract_round_bar_section(steel_elem)
            elif tag.endswith("StbSecFlatBar"):
                section_info = self.extract_flat_bar_section(steel_elem)
            elif tag.endswith("StbSecFiveTypes"):
                section_info = self.extract_five_types_section(steel_elem)
            else:
                logger.warning("Taperの鋼材形状 '%s' は未サポートです", shape_name)
                continue

            if section_info:
                section_info["steel_shape_name"] = shape_name
                if pos == "START":
                    start_info = section_info
                elif pos == "END":
                    end_info = section_info

        if start_info and end_info:
            return {
                "section_type": "TAPERED_S",
                "start_section": start_info,
                "end_section": end_info,
                "stb_name": sec_name,
            }

        return None

    def _extract_rc_haunch_sections(
        self, haunch_elements, sec_name: str
    ) -> Optional[Dict[str, Dict]]:
        """RCハンチ梁の各部位断面情報を抽出"""
        rc_sections: Dict[str, Dict] = {}

        for haunch in haunch_elements:
            pos = haunch.get("pos")
            width = haunch.get("width")
            depth = haunch.get("depth")

            if not pos or not width or not depth:
                logger.warning("haunch要素にpos、width、depthがありません")
                continue

            rc_sections[pos] = {
                "section_type": "RECTANGLE",
                "width": float(width),
                "height": float(depth),
                "stb_name": sec_name,
                "material_type": "RC",
                "stb_structure_type": "RC",
            }

        return rc_sections if rc_sections else None

    def _extract_rc_beam_sections(
        self, sections_element, sections_data: Dict[str, Dict]
    ):
        """RC構造梁断面の抽出"""
        namespaces = self.get_namespaces()

        for sec_rc_elem in sections_element.findall(".//stb:StbSecBeam_RC", namespaces):
            sec_id = sec_rc_elem.get("id")
            sec_name = sec_rc_elem.get("name")

            if not sec_id:
                continue

            logger.debug("RC梁断面 ID %s を検出 (名称: %s)", sec_id, sec_name)

            # ハンチ付きRC梁断面を優先的にチェック
            haunch_elems = sec_rc_elem.findall(
                ".//stb:StbSecFigureBeam_RC/stb:StbSecBeam_RC_Haunch",
                namespaces,
            )

            if haunch_elems:
                haunch_sections = self._extract_rc_haunch_sections(
                    haunch_elems, sec_name
                )
                if haunch_sections:
                    sections_data[sec_id] = {
                        "section_type": "HAUNCH",
                        "haunch_sections": haunch_sections,
                        "stb_name": sec_name,
                        "material_type": "RC",
                        "stb_structure_type": "RC",
                    }
                    logger.debug("ハンチRC梁断面 ID %s を解析しました", sec_id)
                    continue

            # まずテーパー断面を確認
            taper_elems = sec_rc_elem.findall(
                ".//stb:StbSecFigureBeam_RC/stb:StbSecBeam_RC_Taper",
                namespaces,
            )

            if taper_elems:
                start_info = None
                end_info = None
                for taper in taper_elems:
                    pos = taper.get("pos")
                    width = taper.get("width")
                    depth = taper.get("depth")
                    if not pos or not width or not depth:
                        logger.warning(
                            "Section %s の StbSecBeam_RC_Taper に必要な属性がありません",
                            sec_id,
                        )
                        continue

                    info = {
                        "section_type": "RECTANGLE",
                        "width": float(width),
                        "height": float(depth),
                        "stb_name": sec_name,
                        "material_type": "RC",
                        "stb_structure_type": "RC",
                    }

                    if pos == "START":
                        start_info = info
                    elif pos == "END":
                        end_info = info

                if start_info and end_info:
                    sections_data[sec_id] = {
                        "section_type": "TAPERED_RC",
                        "start_section": start_info,
                        "end_section": end_info,
                        "stb_name": sec_name,
                        "material_type": "RC",
                        "stb_structure_type": "RC",
                    }
                    logger.debug(
                        "テーパーRC梁断面 ID %s を解析しました",
                        sec_id,
                    )
                    continue
                else:
                    logger.warning(
                        "ID %s のテーパーRC断面定義が不完全です",
                        sec_id,
                    )
                    continue

            rc_figure = sec_rc_elem.find(
                ".//stb:StbSecFigureBeam_RC/stb:StbSecBeam_RC_Straight",
                namespaces,
            )

            if rc_figure is None:
                logger.warning(
                    "Section ID %s に StbSecBeam_RC_Straight が見つかりません",
                    sec_id,
                )
                continue

            # StbSecBeam_RC要素からstrength_concrete属性を取得
            strength_concrete = sec_rc_elem.get("strength_concrete")

            rc_section_info = self._extract_rc_beam_section_info(
                rc_figure, sec_name, strength_concrete
            )
            if rc_section_info:
                sections_data[sec_id] = rc_section_info
                logger.debug(
                    "RC梁断面 ID %s を解析しました: %s x %s, コンクリート強度: %s",
                    sec_id,
                    rc_section_info["width"],
                    rc_section_info["height"],
                    strength_concrete or "未指定",
                )

    def _extract_rc_beam_section_info(
        self, rc_figure, sec_name: str, strength_concrete: Optional[str] = None
    ) -> Optional[Dict]:
        """RC梁断面情報の抽出"""
        width = rc_figure.get("width")
        depth = rc_figure.get("depth")

        logger.debug(
            "RC梁断面 - 幅: %s, 高さ: %s, コンクリート強度: %s",
            width,
            depth,
            strength_concrete,
        )

        if not width or not depth:
            logger.warning("RC梁断面の幅または高さが不足しています")
            return None

        try:
            result = {
                "section_type": "RECTANGLE",  # ProfileFactoryと互換性のある形式
                "width": float(width),
                "height": float(depth),
                "stb_name": sec_name,
                "material_type": "RC",
                "stb_structure_type": "RC",
            }

            # コンクリート強度が指定されている場合は追加
            if strength_concrete:
                result["strength_concrete"] = strength_concrete
                logger.debug("コンクリート強度を設定しました: %s", strength_concrete)

            return result
        except (TypeError, ValueError) as e:
            logger.warning("Could not parse RC beam parameters: %s", e)
            return None
