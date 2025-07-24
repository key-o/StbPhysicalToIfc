"""XMLパーサーキャッシュ - 性能最適化のためのDOMキャッシュ"""

import xml.etree.ElementTree as ET
from typing import Optional, Dict
from weakref import WeakValueDictionary

from utils.logger import get_logger
from exceptions.custom_errors import XMLParseError


class XMLParserCache:
    """XMLの解析結果をキャッシュして再利用を可能にするクラス"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        # WeakValueDictionaryを使用してメモリリークを防ぐ
        self._cache: Dict[str, ET.Element] = WeakValueDictionary()
        self._content_hashes: Dict[str, str] = {}
    
    def get_or_parse(self, xml_content: str, cache_key: str = None) -> ET.Element:
        """
        XMLコンテンツを解析し、結果をキャッシュする
        
        Args:
            xml_content: XML文字列
            cache_key: キャッシュキー（省略時はコンテンツのハッシュを使用）
        
        Returns:
            解析されたXMLのルート要素
        
        Raises:
            XMLParseError: XML解析に失敗した場合
        """
        if cache_key is None:
            cache_key = str(hash(xml_content))
        
        # キャッシュから取得を試行
        cached_element = self._cache.get(cache_key)
        if cached_element is not None:
            # コンテンツが変更されていないかチェック
            cached_hash = self._content_hashes.get(cache_key)
            current_hash = str(hash(xml_content))
            
            if cached_hash == current_hash:
                self.logger.debug(f"XMLキャッシュヒット: {cache_key}")
                return cached_element
            else:
                self.logger.debug(f"XMLキャッシュ無効化（内容変更）: {cache_key}")
                # キャッシュから削除
                self._cache.pop(cache_key, None)
                self._content_hashes.pop(cache_key, None)
        
        # 新規解析
        try:
            self.logger.debug(f"XML解析開始: {cache_key}")
            root = ET.fromstring(xml_content)
            
            # キャッシュに保存
            self._cache[cache_key] = root
            self._content_hashes[cache_key] = str(hash(xml_content))
            
            self.logger.debug(f"XMLキャッシュ保存: {cache_key}")
            return root
            
        except ET.ParseError as e:
            raise XMLParseError(f"XML解析エラー: {e}") from e
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._cache.clear()
        self._content_hashes.clear()
        self.logger.debug("XMLキャッシュクリア完了")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """キャッシュ統計情報を取得"""
        return {
            "cached_items": len(self._cache),
            "content_hashes": len(self._content_hashes)
        }