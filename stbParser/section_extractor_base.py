from typing import Optional, Dict, Any
from .xml_parser import STBXMLParser
from .unified_section_processor import UnifiedSectionProcessorMixin
import logging


logger = logging.getLogger(__name__)


class BaseSectionExtractor(UnifiedSectionProcessorMixin):
    """共通の断面抽出ユーティリティクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        self.xml_parser = xml_parser
        # StbSecSteel 要素をキャッシュ
        self._steel_section_cache: Dict[str, Any] = {}
        self._build_steel_section_cache()
        # ミックスインを初期化
        super().__init__()

    def _build_steel_section_cache(self):
        """StbSecSteel 以下の断面要素を name 属性でキャッシュに保持"""
        try:
            namespaces = self.get_namespaces()
            sections = self.xml_parser.find_element(".//stb:StbSections")
            steel_root = (
                sections.find(".//stb:StbSecSteel", namespaces)
                if sections is not None
                else None
            )
            if steel_root is None:
                return
            # 全要素を走査して name 属性をキーに保持
            for elem in list(steel_root):
                name = elem.get("name")
                if name:
                    self._steel_section_cache[name] = elem
        except Exception:
            pass

    def get_namespaces(self):
        return self.xml_parser.get_namespaces()

    def find_element(self, xpath: str):
        return self.xml_parser.find_element(xpath)

    def _float_attr(
        self, element, attribute_name: str, default: Optional[float] = None
    ) -> Optional[float]:
        """Helper to convert XML attribute to float, handling missing attributes and conversion errors."""
        value_str = element.get(attribute_name)
        if value_str is None:
            # Attribute not found, return the default value.
            # If default is None, this will correctly return None.
            # No warning here for missing optional attributes if default is None.
            return default
        try:
            return float(value_str)
        except (ValueError, TypeError):
            logger.warning(
                "属性 '%s' ('%s') を float に変換できませんでした (要素: '%s')。既定値 %s を使用します",
                attribute_name,
                value_str,
                element.tag,
                default,
            )
            return default

    def safe_get_float_attr(
        self, element, attr_name: str, default: Optional[float] = None
    ) -> Optional[float]:
        """安全な数値属性取得"""
        try:
            attr_value = element.get(attr_name)
            if attr_value is None:
                return default
            return float(attr_value)
        except (TypeError, ValueError):
            logger.warning(
                "要素 %s の属性 %s を数値に変換できません: %s",
                element.tag,
                attr_name,
                attr_value,
            )
            return default

    def safe_get_str_attr(
        self, element, attr_name: str, default: Optional[str] = None
    ) -> Optional[str]:
        """安全な文字列属性取得"""
        attr_value = element.get(attr_name)
        return attr_value if attr_value is not None else default

    def validate_required_attrs(
        self, element, required_attrs: list, element_desc: str = ""
    ) -> bool:
        """必須属性の検証"""
        missing_attrs = []
        for attr in required_attrs:
            if element.get(attr) is None:
                missing_attrs.append(attr)

        if missing_attrs:
            logger.warning(
                "%s要素の必須属性が不足: %s (要素: %s)",
                element_desc,
                missing_attrs,
                element.tag,
            )
            return False
        return True

    def _extract_l_section_params(self, steel_elem) -> Optional[Dict]:
        """L形鋼断面パラメータの抽出（共通実装）"""
        sec_name = steel_elem.get("name")
        logger.debug("L形鋼断面を抽出: %s", sec_name)

        try:
            b_val = self._float_attr(steel_elem, "B")
            t1_val = self._float_attr(steel_elem, "t1")

            params = {
                "section_type": "L",
                "overall_depth": self._float_attr(steel_elem, "A"),
                "flange_width": b_val,
                "overall_width": b_val,  # IfcLShapeProfileDef では幅として B を使用
                "web_thickness": t1_val,
                "flange_thickness": self._float_attr(steel_elem, "t2"),
                "thickness": t1_val,  # t1 を角材の厚さとして利用
                "internal_fillet_radius": self._float_attr(
                    steel_elem, "r1", default=None
                ),
                "stb_name": sec_name,
            }

            stb_type = steel_elem.get("type")
            if stb_type:
                params["arrangement"] = stb_type

            # 必須パラメータの検証
            required = [
                params["overall_depth"],
                params["overall_width"],
                params["thickness"],
                params["flange_thickness"],
            ]
            if any(v is None for v in required):
                logger.warning("L形鋼 '%s' に必要な属性が不足しています", sec_name)
                return None

            logger.debug("L形鋼パラメータ抽出結果: %s", params)
            return params

        except Exception as e:
            logger.error(
                "L形鋼パラメータ解析エラー (断面名: '%s', 要素タグ: %s): %s",
                sec_name,
                steel_elem.tag,
                e,
            )
            return None

    def _extract_c_section_params(self, steel_elem) -> Optional[Dict]:
        """C形鋼断面パラメータの抽出（共通実装）"""
        sec_name = steel_elem.get("name")
        logger.debug("C形鋼断面を抽出: %s", sec_name)

        try:
            b_val = self._float_attr(steel_elem, "B")

            params = {
                "section_type": "C",
                "overall_depth": self._float_attr(steel_elem, "A"),  # A (高さ)
                "flange_width": b_val,  # B (フランジ幅)
                "overall_width": b_val,  # C形鋼の全体幅もフランジ幅と同じ
                "web_thickness": self._float_attr(steel_elem, "t1"),  # t1 (ウェブ厚)
                "flange_thickness": self._float_attr(
                    steel_elem, "t2"
                ),  # t2 (フランジ厚)
                "internal_fillet_radius": self._float_attr(
                    steel_elem, "r1", default=None
                ),  # r1 (内フィレット半径)
                "stb_name": sec_name,
            }

            stb_type = steel_elem.get("type")
            if stb_type:
                params["arrangement"] = stb_type

            # 必須パラメータの検証 (A, B, t1, t2 は None であってはならない)
            required_params_keys = [
                "overall_depth",
                "flange_width",
                "web_thickness",
                "flange_thickness",
            ]
            missing_required = [
                key for key in required_params_keys if params[key] is None
            ]

            if missing_required:
                logger.warning(
                    "C形鋼断面 '%s' (タグ: %s) に必要な属性 %s がありません。必要な属性: A, B, t1, t2",
                    sec_name,
                    steel_elem.tag,
                    missing_required,
                )
                return None

            logger.debug("C形鋼パラメータ抽出結果: %s", params)
            return params

        except Exception as e:
            logger.error(
                "C形鋼パラメータ解析エラー (断面名: '%s', 要素タグ: %s): %s",
                sec_name,
                steel_elem.tag,
                e,
            )
            return None

    def find_steel_section_by_name(self, sections_element, shape_name: str):
        """キャッシュから指定された形状名のStbSecSteel要素を取得"""
        return self._steel_section_cache.get(shape_name)

    def _tag_localname(self, element) -> str:
        """名前空間接頭辞を除いたタグ名を取得"""
        tag = element.tag
        return tag.split("}", 1)[-1] if "}" in tag else tag

    def _is_tag(self, element, local_name: str) -> bool:
        """指定されたローカル名と要素タグが一致するか判定"""
        return self._tag_localname(element) == local_name

    def extract_box_steel_section(self, box_steel_elem) -> Optional[Dict]:
        """BOX形鋼断面（角形鋼管）の抽出"""
        sec_name = box_steel_elem.get("name")
        logger.debug("BOX形鋼断面を抽出: %s", sec_name)

        try:
            A_attr = box_steel_elem.get("A")
            B_attr = box_steel_elem.get("B")
            t_attr = box_steel_elem.get("t")
            if A_attr is None or B_attr is None or t_attr is None:
                raise ValueError("A/B/t attribute missing")

            A = float(A_attr)  # 高さ
            B = float(B_attr)  # 幅
            t = float(t_attr)  # 板厚
            r_attr = box_steel_elem.get("r")
            r = float(r_attr) if r_attr else None

            result = {
                "section_type": "BOX",
                "outer_height": A,
                "outer_width": B,
                "wall_thickness": t,
                "corner_radius": r,
                "internal_fillet_radius": r,
                "external_fillet_radius": r,
                "stb_name": sec_name,
            }

            logger.debug("BOX断面を抽出成功: %s", result)
            return result

        except (TypeError, ValueError) as e:
            sec_id = box_steel_elem.get("id")
            logger.warning(
                "Section ID %s のBOX形鋼パラメータを解析できません: %s",
                sec_id,
                e,
            )
            logger.debug(
                "BOX属性: A=%s, B=%s, t=%s, r=%s",
                box_steel_elem.get("A"),
                box_steel_elem.get("B"),
                box_steel_elem.get("t"),
                box_steel_elem.get("r"),
            )
            return None

    def extract_h_steel_section(self, h_steel_elem) -> Optional[Dict]:
        """H形鋼断面の抽出"""
        sec_name = h_steel_elem.get("name")
        logger.debug("H形鋼断面を抽出: %s", sec_name)

        try:
            A = float(h_steel_elem.get("A"))  # 全高
            B = float(h_steel_elem.get("B"))  # 全幅
            t1 = float(h_steel_elem.get("t1"))  # ウェブ厚
            t2 = float(h_steel_elem.get("t2"))  # フランジ厚
            r_attr = h_steel_elem.get("r")
            r = float(r_attr) if r_attr else None

            result = {
                "section_type": "H",
                "overall_depth": A,
                "overall_width": B,
                "web_thickness": t1,
                "flange_thickness": t2,
                "fillet_radius": r,
                "stb_name": sec_name,
            }

            logger.debug("H断面を抽出成功: %s", result)
            return result

        except (TypeError, ValueError) as e:
            sec_id = h_steel_elem.get("id")
            logger.warning(
                "Section ID %s のH形鋼パラメータを解析できません: %s",
                sec_id,
                e,
            )
            logger.debug(
                "H属性: A=%s, B=%s, t1=%s, t2=%s, r=%s",
                h_steel_elem.get("A"),
                h_steel_elem.get("B"),
                h_steel_elem.get("t1"),
                h_steel_elem.get("t2"),
                h_steel_elem.get("r"),
            )
            return None

    def extract_build_h_section(self, build_h_elem) -> Optional[Dict]:
        """ビルドH形鋼断面(StbSecBuild-H)の抽出"""
        sec_name = build_h_elem.get("name")
        logger.debug("Build-H 断面を抽出: %s", sec_name)
        try:
            A = float(build_h_elem.get("A"))  # 全高
            B = float(build_h_elem.get("B"))  # 全幅
            t1 = float(build_h_elem.get("t1"))  # ウェブ厚
            t2 = float(build_h_elem.get("t2"))  # フランジ厚
            r_attr = build_h_elem.get("r")
            r = float(r_attr) if r_attr else 0.0

            result = {
                "section_type": "H",
                "overall_depth": A,
                "overall_width": B,
                "web_thickness": t1,
                "flange_thickness": t2,
                "fillet_radius": r,
                "stb_name": sec_name,
            }

            logger.debug("Build-H 断面を抽出成功: %s", result)
            return result

        except (TypeError, ValueError) as e:
            sec_id = build_h_elem.get("id")
            logger.warning(
                "Section ID %s のBuild-Hパラメータを解析できません: %s",
                sec_id,
                e,
            )
            return None

    def extract_c_steel_section(self, c_steel_elem) -> Optional[Dict]:
        """C形鋼断面の抽出"""
        sec_name = c_steel_elem.get("name")
        logger.debug("C形鋼断面を抽出: %s", sec_name)

        try:
            A = float(c_steel_elem.get("A"))  # 全高
            B = float(c_steel_elem.get("B"))  # 全幅
            t1 = float(c_steel_elem.get("t1"))  # ウェブ厚
            t2 = float(c_steel_elem.get("t2"))  # フランジ厚
            r_attr = c_steel_elem.get("r")
            r = float(r_attr) if r_attr else None

            result = {
                "section_type": "C",
                "overall_depth": A,
                "overall_width": B,
                "web_thickness": t1,
                "flange_thickness": t2,
                "fillet_radius": r,
                "stb_name": sec_name,
            }

            logger.debug("C断面を抽出成功: %s", result)
            return result

        except (TypeError, ValueError) as e:
            sec_id = c_steel_elem.get("id")
            logger.warning(
                "Section ID %s のC形鋼パラメータを解析できません: %s",
                sec_id,
                e,
            )
            return None

    def extract_pipe_steel_section(self, pipe_steel_elem) -> Optional[Dict]:
        """円形鋼管断面の抽出"""
        sec_name = pipe_steel_elem.get("name")
        logger.debug("パイプ鋼管断面を抽出: %s", sec_name)

        try:
            # pipe_steel_elem 自体が StbSecPipe 要素
            D = float(pipe_steel_elem.get("D"))  # 外径
            t = float(pipe_steel_elem.get("t"))  # 厚さ

            result = {
                "section_type": "PIPE",
                "outer_diameter": D,
                "wall_thickness": t,
                "stb_name": sec_name,
            }

            logger.debug("パイプ断面を抽出成功: %s", result)
            return result

        except (TypeError, ValueError) as e:
            sec_id = pipe_steel_elem.get("id")
            logger.warning(
                "Section ID %s のパイプパラメータを解析できません: %s",
                sec_id,
                e,
            )
            return None

    def extract_lip_c_section(self, lip_c_elem) -> Optional[Dict]:
        """Lip-C形鋼断面の抽出"""
        sec_name = lip_c_elem.get("name")
        logger.debug("Lip-C形鋼断面を抽出: %s", sec_name)
        try:
            H = float(lip_c_elem.get("H"))
            A = float(lip_c_elem.get("A"))
            t = float(lip_c_elem.get("t"))
            result = {
                "section_type": "C",
                "overall_depth": H,
                "flange_width": A,
                "overall_width": A,
                "web_thickness": t,
                "flange_thickness": t,
                "stb_name": sec_name,
            }
            stb_type = lip_c_elem.get("type")
            if stb_type:
                result["arrangement"] = stb_type
            logger.debug("Lip-C断面を抽出成功: %s", result)
            return result
        except (TypeError, ValueError) as e:
            sec_id = lip_c_elem.get("id")
            logger.warning(
                "Section ID %s のLip-C形鋼パラメータを解析できません: %s",
                sec_id,
                e,
            )
            return None

    def extract_build_box_section(self, build_box_elem) -> Optional[Dict]:
        """ビルドBOX形鋼断面（StbSecBuild-BOX）の抽出"""
        sec_name = build_box_elem.get("name")
        logger.debug("Build-BOX 断面を抽出: %s", sec_name)
        try:
            A_attr = build_box_elem.get("A")
            B_attr = build_box_elem.get("B")
            t1_attr = build_box_elem.get("t1")
            t2_attr = build_box_elem.get("t2")
            if None in (A_attr, B_attr, t1_attr, t2_attr):
                raise ValueError("A/B/t1/t2 attribute missing")

            A = float(A_attr)  # 高さ
            B = float(B_attr)  # 幅
            t1 = float(t1_attr)  # 板厚1
            _t2 = float(t2_attr)  # 板厚2
            # r属性は無い場合が多い
            r_attr = build_box_elem.get("r")
            r = float(r_attr) if r_attr else None
            result = {
                "section_type": "BOX",
                "outer_height": A,
                "outer_width": B,
                "wall_thickness": t1,  # t1を壁厚として扱う
                "wall_thickness_2": _t2,
                "corner_radius": r,
                "stb_name": sec_name,
            }
            logger.debug("Build-BOX 断面を抽出成功: %s", result)
            return result
        except (TypeError, ValueError) as e:
            logger.warning(
                "Build-BOX 断面 %s のパラメータを解析できません: %s",
                sec_name,
                e,
            )
            return None

    def extract_flat_bar_section(self, flatbar_elem) -> Optional[Dict]:
        """フラットバー断面(StbSecFlatBar)の抽出"""
        sec_name = flatbar_elem.get("name")
        logger.debug("フラットバー断面を抽出: %s", sec_name)
        try:
            B = float(flatbar_elem.get("B"))
            t = float(flatbar_elem.get("t"))
            result = {
                "section_type": "RECTANGLE",
                "width": B,
                "height": t,
                "stb_name": sec_name,
            }
            logger.debug("フラットバー断面を抽出成功: %s", result)
            return result
        except (TypeError, ValueError) as e:
            sec_id = flatbar_elem.get("id")
            logger.warning(
                "Section ID %s のフラットバー断面を解析できません: %s",
                sec_id,
                e,
            )
            return None

    def extract_round_bar_section(self, roundbar_elem) -> Optional[Dict]:
        """丸鋼断面(StbSecRoundBar)の抽出"""
        sec_name = roundbar_elem.get("name")
        logger.debug("丸鋼断面を抽出: %s", sec_name)
        try:
            radius = float(roundbar_elem.get("R"))
            result = {
                "section_type": "CIRCLE",
                "radius": radius,
                "stb_name": sec_name,
            }
            logger.debug("丸鋼断面を抽出成功: %s", result)
            return result
        except (TypeError, ValueError) as e:
            sec_id = roundbar_elem.get("id")
            logger.warning(
                "Section ID %s の丸鋼断面を解析できません: %s",
                sec_id,
                e,
            )
            return None

    def extract_steel_sections_generic(
        self, sections_element, section_xpath: str, processor_func
    ) -> Dict[str, Dict]:
        """鋼構造断面の汎用抽出メソッド"""
        namespaces = self.get_namespaces()
        sections_data = {}

        for sec_elem in sections_element.findall(section_xpath, namespaces):
            sec_id = sec_elem.get("id")
            sec_name = sec_elem.get("name")

            if not sec_id:
                continue

            try:
                section_info = processor_func(sec_elem, sections_element, namespaces)
                if section_info:
                    sections_data[sec_id] = section_info
                    logger.debug("断面ID %s を正常に抽出", sec_id)
            except Exception as e:
                logger.warning("断面ID %s の抽出でエラー: %s", sec_id, e)
                continue

        return sections_data

    def extract_rc_sections_generic(
        self, sections_element, section_xpath: str, processor_func
    ) -> Dict[str, Dict]:
        """RC構造断面の汎用抽出メソッド"""
        namespaces = self.get_namespaces()
        sections_data = {}

        for sec_elem in sections_element.findall(section_xpath, namespaces):
            sec_id = sec_elem.get("id")
            sec_name = sec_elem.get("name")

            if not sec_id:
                continue

            try:
                section_info = processor_func(sec_elem, sections_element, namespaces)
                if section_info:
                    sections_data[sec_id] = section_info
                    logger.debug("RC断面ID %s を正常に抽出", sec_id)
            except Exception as e:
                logger.warning("RC断面ID %s の抽出でエラー: %s", sec_id, e)
                continue

        return sections_data

    def find_same_steel_element(
        self, sec_elem, same_xpath: str, namespaces
    ) -> Optional[Dict]:
        """Same構成の鋼材断面要素を検索・抽出する共通メソッド"""
        same_elem = sec_elem.find(same_xpath, namespaces)
        if same_elem is None:
            return None

        shape_name = same_elem.get("shape")
        strength_main = same_elem.get("strength_main")

        if not shape_name:
            return None

        steel_elem = self.find_steel_section_by_name(None, shape_name)
        if steel_elem is None:
            logger.warning("形状 '%s' 用の鋼材断面が見つかりません", shape_name)
            return None

        return {
            "same_elem": same_elem,
            "steel_elem": steel_elem,
            "shape_name": shape_name,
            "strength_main": strength_main,
        }

    def find_straight_steel_element(
        self, sec_elem, straight_xpath: str, namespaces
    ) -> Optional[Dict]:
        """Straight構成の鋼材断面要素を検索・抽出する共通メソッド（梁用）"""
        straight_elem = sec_elem.find(straight_xpath, namespaces)
        if straight_elem is None:
            return None

        shape_name = straight_elem.get("shape")
        strength_main = straight_elem.get("strength_main")

        if not shape_name:
            return None

        steel_elem = self.find_steel_section_by_name(None, shape_name)
        if steel_elem is None:
            logger.warning("形状 '%s' 用の鋼材断面が見つかりません", shape_name)
            return None

        return {
            "straight_elem": straight_elem,
            "steel_elem": steel_elem,
            "shape_name": shape_name,
            "strength_main": strength_main,
        }

    def process_steel_shape_params(self, steel_elem, sec_name: str) -> Optional[Dict]:
        """鋼材形状から断面パラメータを抽出する共通メソッド"""
        try:
            tag = steel_elem.tag
            # 元のコードと同じ部分文字列マッチを使用
            if "Roll-H" in tag or tag.endswith("Roll-H"):
                return self.extract_h_steel_section(steel_elem)
            elif "Build-H" in tag or tag.endswith("Build-H"):
                return self.extract_build_h_section(steel_elem)
            elif "Roll-BOX" in tag or tag.endswith("Roll-BOX"):
                return self.extract_box_steel_section(steel_elem)
            elif "Build-BOX" in tag or tag.endswith("Build-BOX"):
                return self.extract_build_box_section(steel_elem)
            elif "Roll-C" in tag or tag.endswith("Roll-C"):
                return self._extract_c_section_params(steel_elem)
            elif "Roll-L" in tag or tag.endswith("Roll-L"):
                return self._extract_l_section_params(steel_elem)
            elif "Pipe" in tag or tag.endswith("Pipe"):
                return self.extract_pipe_steel_section(steel_elem)
            elif "RoundBar" in tag:
                return self.extract_round_bar_section(steel_elem)
            elif "FlatBar" in tag:
                return self.extract_flat_bar_section(steel_elem)
            elif "LipC" in tag:
                return self.extract_lip_c_section(steel_elem)
            else:
                logger.warning("未対応の鋼材形状: %s (断面名: %s)", tag, sec_name)
                return None
        except Exception as e:
            logger.error("鋼材形状パラメータ抽出エラー (断面名: %s): %s", sec_name, e)
            return None

    def extract_five_types_section(self, steel_elem) -> Optional[Dict]:
        """FiveTypes断面（複合断面）の抽出"""
        sec_name = steel_elem.get("name")
        logger.debug("FiveTypes断面を抽出: %s", sec_name)
        
        try:
            # nameから断面タイプを判定
            if not sec_name:
                logger.warning("FiveTypes断面にname属性がありません")
                return None
            
            # 複合断面の解析
            if sec_name.startswith("2CB-"):
                return self._extract_double_channel_back_to_back(sec_name)
            elif sec_name.startswith("2CF-"):
                return self._extract_double_channel_face_to_face(sec_name)
            elif sec_name.startswith("2[-"):
                return self._extract_double_built_up_section(sec_name)
            elif sec_name.startswith("[-"):
                return self._extract_single_built_up_section(sec_name)
            else:
                logger.warning("未対応のFiveTypes断面名: %s", sec_name)
                return None
                
        except Exception as e:
            logger.error("FiveTypes断面解析エラー (断面名: %s): %s", sec_name, e)
            return None

    def _extract_double_channel_back_to_back(self, name: str) -> Optional[Dict]:
        """2CB（背中合わせチャンネル）断面の抽出"""
        try:
            # 2CB-100x50x5x7.5 のような形式を解析
            parts = name.replace("2CB-", "").split("x")
            if len(parts) < 4:
                logger.warning("2CB断面名の形式が不正: %s", name)
                return None
            
            depth = float(parts[0])     # A (高さ)
            width = float(parts[1])     # B (フランジ幅)
            web_thick = float(parts[2]) # t1 (ウェブ厚)
            flange_thick = float(parts[3]) # t2 (フランジ厚)
            
            section_dict = {
                "section_type": "COMPOUND_CHANNEL",
                "arrangement": "BACK_TO_BACK",
                "overall_depth": depth,
                "overall_width": width * 2,  # 2つ分の幅
                "flange_width": width,
                "web_thickness": web_thick,
                "flange_thickness": flange_thick,
                "stb_name": name,
            }
            
            logger.debug("2CB断面を抽出: %s", section_dict)
            return section_dict
            
        except (ValueError, IndexError) as e:
            logger.warning("2CB断面パラメータ解析エラー (%s): %s", name, e)
            return None

    def _extract_double_channel_face_to_face(self, name: str) -> Optional[Dict]:
        """2CF（向かい合わせチャンネル）断面の抽出"""
        try:
            # 2CF-100x50x5x7.5 のような形式を解析
            parts = name.replace("2CF-", "").split("x")
            if len(parts) < 4:
                logger.warning("2CF断面名の形式が不正: %s", name)
                return None
            
            depth = float(parts[0])     # A (高さ)
            width = float(parts[1])     # B (フランジ幅)
            web_thick = float(parts[2]) # t1 (ウェブ厚)
            flange_thick = float(parts[3]) # t2 (フランジ厚)
            
            section_dict = {
                "section_type": "COMPOUND_CHANNEL",
                "arrangement": "FACE_TO_FACE",
                "overall_depth": depth,
                "overall_width": width * 2,  # 2つ分の幅
                "flange_width": width,
                "web_thickness": web_thick,
                "flange_thickness": flange_thick,
                "stb_name": name,
            }
            
            logger.debug("2CF断面を抽出: %s", section_dict)
            return section_dict
            
        except (ValueError, IndexError) as e:
            logger.warning("2CF断面パラメータ解析エラー (%s): %s", name, e)
            return None

    def _extract_double_built_up_section(self, name: str) -> Optional[Dict]:
        """2[-（二重山形鋼）断面の抽出"""
        try:
            # 2[-100x100x7 のような形式を解析
            parts = name.replace("2[-", "").split("x")
            if len(parts) < 3:
                logger.warning("2[-断面名の形式が不正: %s", name)
                return None
            
            a = float(parts[0])         # A (脚長1)
            b = float(parts[1])         # B (脚長2)
            thickness = float(parts[2]) # t (厚さ)
            
            section_dict = {
                "section_type": "COMPOUND_L",
                "arrangement": "DOUBLE",
                "overall_depth": a,
                "overall_width": b,
                "thickness": thickness,
                "flange_thickness": thickness,
                "web_thickness": thickness,
                "stb_name": name,
            }
            
            logger.debug("2[-断面を抽出: %s", section_dict)
            return section_dict
            
        except (ValueError, IndexError) as e:
            logger.warning("2[-断面パラメータ解析エラー (%s): %s", name, e)
            return None

    def _extract_single_built_up_section(self, name: str) -> Optional[Dict]:
        """[-（単一山形鋼）断面の抽出"""
        try:
            # [-100x100x7 のような形式を解析
            parts = name.replace("[-", "").split("x")
            if len(parts) < 3:
                logger.warning("[-断面名の形式が不正: %s", name)
                return None
            
            a = float(parts[0])         # A (脚長1)
            b = float(parts[1])         # B (脚長2)
            thickness = float(parts[2]) # t (厚さ)
            
            section_dict = {
                "section_type": "L",
                "overall_depth": a,
                "overall_width": b,
                "thickness": thickness,
                "flange_thickness": thickness,
                "web_thickness": thickness,
                "stb_name": name,
            }
            
            logger.debug("[-断面を抽出: %s", section_dict)
            return section_dict
            
        except (ValueError, IndexError) as e:
            logger.warning("[-断面パラメータ解析エラー (%s): %s", name, e)
            return None

