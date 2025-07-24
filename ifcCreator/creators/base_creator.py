"""Base Element Creator

v2.2.0 統合ベース要素作成クラス
全ての要素作成クラスの基底クラス
"""

from typing import Optional, Any, Dict, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseElementCreator(ABC):
    """統合ベース要素作成クラス
    
    v2.2.0: 全Creator共通の基底機能を提供
    """
    
    def __init__(self, project_builder=None):
        """初期化
        
        Args:
            project_builder: IFCプロジェクトビルダー
        """
        self.project_builder = project_builder
        self.logger = logger.getChild(self.__class__.__name__)
        self._element_count = 0
        
    @abstractmethod
    def create_element(self, definition: Dict[str, Any]) -> Optional[Any]:
        """要素を作成（サブクラスで実装）
        
        Args:
            definition: 要素定義辞書
            
        Returns:
            作成されたIFC要素、失敗時はNone
        """
        pass
    
    def create_elements(self, definitions: List[Dict[str, Any]]) -> List[Any]:
        """複数要素を作成
        
        Args:
            definitions: 要素定義リスト
            
        Returns:
            作成されたIFC要素のリスト
        """
        elements = []
        for i, definition in enumerate(definitions):
            try:
                element = self.create_element(definition)
                if element:
                    elements.append(element)
                    self._element_count += 1
            except Exception as e:
                self.logger.error(f"Element {i} creation failed: {e}")
                
        self.logger.info(f"Created {len(elements)} elements")
        return elements
    
    @property
    def element_count(self) -> int:
        """作成された要素数を取得"""
        return self._element_count
    
    def reset_count(self):
        """要素数カウンタをリセット"""
        self._element_count = 0


class LinearElementCreator(BaseElementCreator):
    """線要素作成ベースクラス（梁・柱・ブレース用）"""
    
    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "linear"


class PlanarElementCreator(BaseElementCreator):
    """面要素作成ベースクラス（スラブ・壁用）"""
    
    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "planar"


class FoundationElementCreator(BaseElementCreator):
    """基礎要素作成ベースクラス（杭・フーチング・基礎柱用）"""
    
    def __init__(self, project_builder=None):
        super().__init__(project_builder)
        self.element_type = "foundation"


# v2.2.0 統合後の下位互換性のためのエイリアス
StructuralElementCreatorBase = BaseElementCreator