"""要素データの出力を行うサービス"""

from typing import Dict, Any

from utils.logger import get_logger
from common import save_json


class ElementOutputService:
    """要素データのJSON出力を管理するサービス"""
    
    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__)
    
    def save_element_json(
        self, element_defs: list, output_path: str, element_type: str
    ):
        """要素定義をJSONファイルに保存"""
        try:
            save_json(element_defs, output_path)
            self.logger.info("%s定義を %s に書き出しました", element_type, output_path)
        except IOError as e:
            self.logger.error("JSON保存エラー (%s): %s", element_type, e)
            raise
    
    def save_all_element_jsons(
        self, conversion_result: Dict[str, Any], base_filename: str, debug_enabled: bool = False
    ):
        """全ての要素定義をJSONファイルに保存（デバッグモード時のみ）"""
        if not debug_enabled:
            self.logger.debug("デバッグモード無効のため、JSON出力をスキップします")
            return
        
        element_mappings = {
            "beam_defs": ("梁", "_beams.json"),
            "column_defs": ("柱", "_columns.json"),
            "brace_defs": ("ブレース", "_braces.json"),
            "pile_defs": ("杭", "_piles.json"),
            "slab_defs": ("スラブ", "_slabs.json"),
            "wall_defs": ("壁", "_walls.json"),
            "footing_defs": ("フーチング", "_footings.json"),
        }
        
        self.logger.debug("デバッグモード有効 - JSON出力を開始します")
        for key, (element_type, suffix) in element_mappings.items():
            element_defs = conversion_result.get(key, [])
            if element_defs:
                output_path = base_filename.replace(".stb", suffix)
                self.save_element_json(element_defs, output_path, element_type)