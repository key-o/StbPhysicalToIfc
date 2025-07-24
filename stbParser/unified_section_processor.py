# unified_section_processor.py
"""
Section Extractor共通処理の統一化
重複していた処理パターンを分離・統一
"""

from typing import Optional, Dict, List, Callable
import logging

logger = logging.getLogger(__name__)


class SteelShapeDispatcher:
    """鋼材断面形状の統一ディスパッチャー"""
    
    def __init__(self, base_extractor):
        self.base = base_extractor
        
    def dispatch_steel_shape(self, steel_elem, context_info: Dict = None) -> Optional[Dict]:
        """鋼材断面形状の統一ディスパッチ処理"""
        try:
            # 形状タイプを判定して適切な処理メソッドを呼び出し
            if self._is_tag(steel_elem, "StbSecBuild-H"):
                return self.base.extract_build_h_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecRoll-H"):
                return self.base.extract_h_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecPipe"):
                return self.base.extract_pipe_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecBuild-BOX"):
                return self.base.extract_build_box_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecRoll-BOX"):
                return self.base.extract_box_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecBuild-T"):
                return self.base.extract_build_t_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecRoll-T"):
                return self.base.extract_t_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecRoll-C"):
                return self.base.extract_c_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecRoll-L"):
                return self.base.extract_l_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecLipC"):
                return self.base.extract_lip_c_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecRoll-FB"):
                return self.base.extract_fb_steel_section(steel_elem)
            elif self._is_tag(steel_elem, "StbSecRoundBar"):
                return self.base.extract_round_bar_section(steel_elem)
            else:
                logger.warning("未対応の鋼材断面形状: %s", steel_elem.tag if steel_elem is not None else "None")
                return None
                
        except Exception as e:
            logger.error("鋼材断面形状処理中にエラー: %s", e)
            return None
    
    def _is_tag(self, element, tag_name: str) -> bool:
        """要素のタグ名を安全にチェック"""
        return element is not None and element.tag.endswith(tag_name)


class SameNotSamePatternProcessor:
    """Same/NotSameパターンの統一処理"""
    
    def __init__(self, base_extractor):
        self.base = base_extractor
        
    def process_same_notsame_pattern(self, steel_fig_elem, shape_processor_func: Callable, context_info: Dict = None) -> List[Dict]:
        """Same/NotSame パターンの統一処理
        
        Args:
            steel_fig_elem: StbSecSteelFigure* 要素
            shape_processor_func: 個別形状処理関数
            context_info: コンテキスト情報
            
        Returns:
            処理結果のリスト
        """
        results = []
        namespaces = self.base.get_namespaces()
        
        try:
            # Same パターンを探す
            same_elem = self._find_same_element(steel_fig_elem, namespaces)
            if same_elem is not None:
                result = self._process_same_element(same_elem, shape_processor_func, context_info)
                if result:
                    results.append(result)
                    
            # NotSame パターンを探す  
            not_same_elems = self._find_notsame_elements(steel_fig_elem, namespaces)
            for not_same_elem in not_same_elems:
                result = self._process_notsame_element(not_same_elem, shape_processor_func, context_info)
                if result:
                    results.append(result)
                    
        except Exception as e:
            logger.error("Same/NotSame パターン処理中にエラー: %s", e)
            
        return results

    def _find_same_element(self, steel_fig_elem, namespaces):
        """Same要素を検索（複数パターンに対応）"""
        same_patterns = [
            "stb:StbSecSteelColumn_S_Same",
            "stb:StbSecSteelColumn_CFT_Same",
            "stb:StbSecSteelColumn_SRC_Same",
            "stb:StbSecSteelBeam_S_Same", 
            "stb:StbSecSteelBrace_S_Same",
            "stb:StbSecSteelGirder_S_Same"
        ]
        
        for pattern in same_patterns:
            same_elem = steel_fig_elem.find(pattern, namespaces)
            if same_elem is not None:
                return same_elem
        return None

    def _find_notsame_elements(self, steel_fig_elem, namespaces):
        """NotSame要素群を検索（複数パターンに対応）"""
        notsame_patterns = [
            "stb:StbSecSteelColumn_S_NotSame",
            "stb:StbSecSteelColumn_CFT_NotSame",
            "stb:StbSecSteelColumn_SRC_NotSame",
            "stb:StbSecSteelBeam_S_NotSame",
            "stb:StbSecSteelBrace_S_NotSame", 
            "stb:StbSecSteelGirder_S_NotSame"
        ]
        
        results = []
        for pattern in notsame_patterns:
            elements = steel_fig_elem.findall(pattern, namespaces)
            results.extend(elements)
        return results

    def _process_same_element(self, same_elem, shape_processor_func, context_info):
        """Same要素の処理"""
        try:
            shape_name = same_elem.get("shape")
            strength_main = same_elem.get("strength_main")
            
            if shape_name and shape_name in self.base._steel_section_cache:
                steel_elem = self.base._steel_section_cache[shape_name]
                section_dict = shape_processor_func(steel_elem, same_elem)
                if section_dict:
                    if strength_main:
                        section_dict["strength_main"] = strength_main
                    # STBの断面名を設定（コンテキスト情報から取得）
                    if context_info and context_info.get("sec_name"):
                        section_dict["stb_name"] = context_info["sec_name"]
                return section_dict
            else:
                logger.warning("Same要素の形状名が見つかりません: %s", shape_name)
                return None
                
        except Exception as e:
            logger.error("Same要素処理中にエラー: %s", e)
            return None

    def _process_notsame_element(self, not_same_elem, shape_processor_func, context_info):
        """NotSame要素の処理"""
        try:
            shape_name = not_same_elem.get("shape")
            strength_main = not_same_elem.get("strength_main")
            pos = not_same_elem.get("pos", "TOP")  # デフォルトはTOP
            
            if shape_name and shape_name in self.base._steel_section_cache:
                steel_elem = self.base._steel_section_cache[shape_name]
                section_dict = shape_processor_func(steel_elem, not_same_elem)
                if section_dict:
                    if strength_main:
                        section_dict["strength_main"] = strength_main
                    section_dict["position"] = pos
                    # STBの断面名を設定（コンテキスト情報から取得）
                    if context_info and context_info.get("sec_name"):
                        section_dict["stb_name"] = context_info["sec_name"]
                return section_dict
            else:
                logger.warning("NotSame要素の形状名が見つかりません: %s", shape_name)
                return None
                
        except Exception as e:
            logger.error("NotSame要素処理中にエラー: %s", e)
            return None


class RCShapeProcessor:
    """RC断面形状の統一処理"""
    
    def __init__(self, base_extractor):
        self.base = base_extractor
        
    def process_rc_shape(self, rc_fig_elem, context_info: Dict = None) -> Optional[Dict]:
        """RC断面形状の統一ディスパッチ処理"""
        try:
            namespaces = self.base.get_namespaces()
            
            # 矩形断面
            rect_elem = rc_fig_elem.find("stb:StbSecRC_Rect", namespaces)
            if rect_elem is not None:
                return self._process_rc_rect_section(rect_elem, context_info)
                
            # 円形断面  
            circle_elem = rc_fig_elem.find("stb:StbSecRC_Circle", namespaces)
            if circle_elem is not None:
                return self._process_rc_circle_section(circle_elem, context_info)
                
            # その他の形状（必要に応じて追加）
            logger.warning("未対応のRC断面形状: %s", rc_fig_elem.tag if rc_fig_elem is not None else "None")
            return None
            
        except Exception as e:
            logger.error("RC断面形状処理中にエラー: %s", e)
            return None

    def _process_rc_rect_section(self, rect_elem, context_info):
        """RC矩形断面の処理"""
        try:
            width_x = self.base._float_attr(rect_elem, "width_X")
            width_y = self.base._float_attr(rect_elem, "width_Y")
            
            section_dict = {
                "section_type": "RECTANGLE",
                "width": width_x,
                "height": width_y,
                "material_type": "RC",
            }
            
            # コンテキストに応じた追加情報
            if context_info:
                section_dict.update(context_info)
                
            return section_dict
            
        except Exception as e:
            logger.error("RC矩形断面処理中にエラー: %s", e)
            return None

    def _process_rc_circle_section(self, circle_elem, context_info):
        """RC円形断面の処理"""
        try:
            radius = self.base._float_attr(circle_elem, "D") 
            if radius:
                radius = radius / 2.0  # 直径から半径に変換
                
            section_dict = {
                "section_type": "CIRCLE", 
                "radius": radius,
                "diameter": self.base._float_attr(circle_elem, "D"),
                "material_type": "RC",
            }
            
            # コンテキストに応じた追加情報
            if context_info:
                section_dict.update(context_info)
                
            return section_dict
            
        except Exception as e:
            logger.error("RC円形断面処理中にエラー: %s", e)
            return None


class UnifiedSectionProcessorMixin:
    """統一Section Processorのミックスイン
    
    既存のBaseSectionExtractorに統一処理機能を追加
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 統一処理クラスを初期化
        self.steel_dispatcher = SteelShapeDispatcher(self)
        self.same_notsame_processor = SameNotSamePatternProcessor(self)
        self.rc_processor = RCShapeProcessor(self)
        
    def dispatch_steel_shape(self, steel_elem, context_info: Dict = None) -> Optional[Dict]:
        """鋼材断面形状の統一ディスパッチ（ミックスイン用）"""
        return self.steel_dispatcher.dispatch_steel_shape(steel_elem, context_info)
        
    def process_same_notsame_pattern(self, steel_fig_elem, shape_processor_func: Callable, context_info: Dict = None) -> List[Dict]:
        """Same/NotSameパターンの統一処理（ミックスイン用）"""
        return self.same_notsame_processor.process_same_notsame_pattern(
            steel_fig_elem, shape_processor_func, context_info
        )
        
    def process_rc_shape(self, rc_fig_elem, context_info: Dict = None) -> Optional[Dict]:
        """RC断面形状の統一処理（ミックスイン用）"""
        return self.rc_processor.process_rc_shape(rc_fig_elem, context_info)