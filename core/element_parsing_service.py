"""STB要素の解析を行うサービス"""

from typing import Dict, Any, Optional, List

from utils.logger import get_logger
from common.xml_parser_cache import XMLParserCache
from stbParser.unified_stb_parser import UnifiedSTBParser, ElementType


class ElementParsingService:
    """STB要素の解析を統合管理するサービス"""

    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__)
        self.xml_cache = XMLParserCache()
        self.selected_categories: Optional[List[str]] = None

    def parse_beams(self, stb_content: str) -> list:
        """梁要素を解析"""
        return self.parse_element_type(stb_content, ElementType.BEAM)

    def parse_columns(self, stb_content: str) -> list:
        """柱要素を解析"""
        return self.parse_element_type(stb_content, ElementType.COLUMN)

    def parse_braces(self, stb_content: str) -> list:
        """ブレース要素を解析"""
        return self.parse_element_type(stb_content, ElementType.BRACE)

    def parse_piles(self, stb_content: str) -> list:
        """杭要素を解析"""
        return self.parse_element_type(stb_content, ElementType.PILE)

    def parse_slabs(self, stb_content: str) -> list:
        """スラブ要素を解析"""
        return self.parse_element_type(stb_content, ElementType.SLAB)

    def parse_walls(self, stb_content: str) -> list:
        """壁要素を解析"""
        return self.parse_element_type(stb_content, ElementType.WALL)

    def parse_footings(self, stb_content: str) -> list:
        """フーチング要素を解析"""
        return self.parse_element_type(stb_content, ElementType.FOOTING)

    def parse_foundation_columns(self, stb_content: str) -> list:
        """基礎柱要素を解析"""
        return self.parse_element_type(stb_content, ElementType.FOUNDATION_COLUMN)

    def parse_stories(self, stb_content: str) -> list:
        """階層要素を解析"""
        return self.parse_element_type(stb_content, ElementType.STORY)

    def parse_axes(self, stb_content: str) -> list:
        """通芯要素を解析"""
        return self.parse_element_type(stb_content, ElementType.AXES)

    def parse_element_type(self, stb_content: str, element_type: ElementType) -> list:
        """指定された要素タイプを解析（汎用）"""
        self.logger.debug(f"--- {element_type.value}を解析中 ---")
        parser = UnifiedSTBParser(stb_content)
        element_defs = parser.parse_element_type(element_type)
        self.logger.debug(f"{element_type.value}定義数: %d", len(element_defs))
        return element_defs

    def set_selected_categories(self, categories: Optional[List[str]]) -> None:
        """変換対象カテゴリを設定
        
        Args:
            categories: 変換対象カテゴリリスト（None=全て変換）
        """
        if categories:
            # 有効なカテゴリ名のみ保持
            valid_categories = []
            element_type_values = [e.value for e in ElementType]
            
            for category in categories:
                if category.lower() in element_type_values:
                    valid_categories.append(category.lower())
                else:
                    self.logger.warning(f"無効なカテゴリが指定されました: {category}")
            
            self.selected_categories = valid_categories if valid_categories else None
            if self.selected_categories:
                self.logger.info(f"変換対象カテゴリ: {', '.join(self.selected_categories)}")
            else:
                self.logger.info("全てのカテゴリを変換対象とします")
        else:
            self.selected_categories = None

    def _should_parse_category(self, category: str) -> bool:
        """指定されたカテゴリを解析すべきかチェック"""
        if self.selected_categories is None:
            return True
        return category.lower() in self.selected_categories

    def parse_all_elements(self, stb_content: str) -> Dict[str, Any]:
        """全ての要素を解析（XMLキャッシュ使用で性能向上、カテゴリフィルタリング対応）"""
        # 事前にXMLを解析してキャッシュに保存
        cache_key = "main_stb_content"
        try:
            self.xml_cache.get_or_parse(stb_content, cache_key)
            self.logger.debug("STB XMLをキャッシュに保存しました")
        except Exception as e:
            self.logger.warning(f"XMLキャッシュ保存に失敗: {e}")
            # キャッシュ失敗時も処理を継続

        # カテゴリフィルタリングに基づいて各要素を解析
        result = {}
        
        # 梁
        if self._should_parse_category("beam"):
            result["beam_defs"] = self.parse_beams(stb_content)
        else:
            result["beam_defs"] = []
            
        # 柱
        if self._should_parse_category("column"):
            result["column_defs"] = self.parse_columns(stb_content)
        else:
            result["column_defs"] = []
            
        # ブレース
        if self._should_parse_category("brace"):
            result["brace_defs"] = self.parse_braces(stb_content)
        else:
            result["brace_defs"] = []
            
        # 杭
        if self._should_parse_category("pile"):
            result["pile_defs"] = self.parse_piles(stb_content)
        else:
            result["pile_defs"] = []
            
        # スラブ
        if self._should_parse_category("slab"):
            result["slab_defs"] = self.parse_slabs(stb_content)
        else:
            result["slab_defs"] = []
            
        # 壁
        if self._should_parse_category("wall"):
            result["wall_defs"] = self.parse_walls(stb_content)
        else:
            result["wall_defs"] = []
            
        # フーチング
        if self._should_parse_category("footing"):
            result["footing_defs"] = self.parse_footings(stb_content)
        else:
            result["footing_defs"] = []
            
        # 基礎柱
        if self._should_parse_category("foundation_column"):
            result["foundation_column_defs"] = self.parse_foundation_columns(stb_content)
        else:
            result["foundation_column_defs"] = []
            
        # 階層（常に必要）
        result["story_defs"] = self.parse_stories(stb_content)
        
        # 通芯（常に必要）
        result["axes_defs"] = self.parse_axes(stb_content)
        
        return result
