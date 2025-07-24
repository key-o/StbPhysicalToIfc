"""変換サービスクラス - メイン変換処理のオーケストレーション"""

from typing import Dict, Any, Optional, List

from utils.logger import get_logger
from core.stb_file_service import StbFileService
from core.element_parsing_service import ElementParsingService
from core.element_output_service import ElementOutputService
from core.default_story_service import DefaultStoryService
from core.ifc_generation_service import IfcGenerationService


class ConversionService:
    """ST-Bridge から IFC への変換プロセス全体をオーケストレーションするサービス"""

    def __init__(self, logger=None, debug_enabled=False):
        self.logger = logger or get_logger(__name__)
        self.stb_content = None
        self.debug_enabled = debug_enabled

        # 依存サービスを初期化
        self.file_service = StbFileService(logger)
        self.parsing_service = ElementParsingService(logger)
        self.output_service = ElementOutputService(logger)
        self.story_service = DefaultStoryService(logger)
        self.ifc_generation_service = IfcGenerationService(logger, conversion_service=self)

    def load_stb_file(self, file_path: str) -> str:
        """STBファイルを読み込み、内容を返す"""
        return self.file_service.load_stb_file(file_path)

    def set_selected_categories(self, categories: Optional[List[str]]) -> None:
        """変換対象カテゴリを設定
        
        Args:
            categories: 変換対象カテゴリリスト（None=全て変換）
        """
        self.parsing_service.set_selected_categories(categories)

    def parse_all_elements(self, stb_content: str) -> Dict[str, Any]:
        """全ての要素を解析"""
        return self.parsing_service.parse_all_elements(stb_content)

    def save_all_element_jsons(
        self, conversion_result: Dict[str, Any], base_filename: str
    ):
        """全ての要素定義をJSONファイルに保存（デバッグモード時のみ）"""
        self.output_service.save_all_element_jsons(
            conversion_result, base_filename, self.debug_enabled
        )

    # === Main Conversion Methods ===

    def convert_stb_to_ifc(
        self, stb_content: str, base_filename: str
    ) -> Dict[str, Any]:
        """STB内容をIFC要素に変換し、結果を返す"""

        # STBコンテンツを保持
        self.stb_content = stb_content

        # 全要素を解析
        conversion_result = self.parse_all_elements(stb_content)

        # JSON出力
        self.save_all_element_jsons(conversion_result, base_filename)

        return conversion_result

    def create_ifc_file(
        self, conversion_result: Dict[str, Any], output_filename: str
    ) -> bool:
        """変換結果からIFCファイルを生成"""
        return self.ifc_generation_service.create_ifc_file(
            conversion_result, output_filename, self.stb_content
        )

    # === DefaultStoryGenerator Methods (Delegated) ===
    
    def create_default_story(self, **kwargs) -> list:
        """デフォルトStoryを生成（DefaultStoryServiceに委譲）"""
        return self.story_service.create_default_story(**kwargs)
    
    def should_use_default_story(self, story_defs) -> bool:
        """デフォルトStoryを使用すべきかどうかを判定（DefaultStoryServiceに委譲）"""
        return self.story_service.should_use_default_story(story_defs)
