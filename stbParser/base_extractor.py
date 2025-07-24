# base_extractor.py
"""
ST-Bridge要素抽出のベースクラスと共通フレームワーク
各Extractorの重複処理を共通化
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from .xml_parser import STBXMLParser
from common.extractor_utils import StoryMappingUtils
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContainerConfig:
    """要素コンテナの設定"""
    container_tag: str  # コンテナのXMLタグ名（例：StbGirders）
    element_tag: str    # 要素のXMLタグ名（例：StbGirder）
    element_type: str   # 要素タイプ（ログ用、例：StbGirder）


@dataclass
class ExtractionConfig:
    """抽出設定"""
    containers: List[ContainerConfig]
    result_name: str  # 結果の名前（例：beam_defs）


class BaseExtractor(ABC):
    """ST-Bridge要素抽出のベースクラス"""
    
    def __init__(self, xml_parser: STBXMLParser):
        """
        Args:
            xml_parser: 初期化済みのSTBXMLParserインスタンス
        """
        self.xml_parser = xml_parser
    
    def extract_elements(
        self, 
        nodes_data: Dict[str, Dict], 
        sections_data: Dict[str, Dict],
        extraction_config: ExtractionConfig
    ) -> List[Dict]:
        """共通の要素抽出処理
        
        Args:
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書
            extraction_config: 抽出設定
            
        Returns:
            抽出された要素定義のリスト
        """
        # 1. 結果リストを初期化
        element_defs = []
        
        # 2. 階層マッピングを作成
        node_story_map = StoryMappingUtils.create_node_story_map(self.xml_parser)
        
        # 3. StbMembersコンテナを検索
        stb_members_element = self._find_stb_members()
        if stb_members_element is None:
            return element_defs
        
        # 4. XMLネームスペースを取得
        namespaces = self.xml_parser.get_namespaces()
        
        # 5-6. 設定に基づいて要素を抽出
        for container_config in extraction_config.containers:
            container_elements = self._extract_from_container(
                stb_members_element,
                container_config,
                nodes_data,
                sections_data,
                node_story_map,
                namespaces
            )
            element_defs.extend(container_elements)
        
        logger.info(
            "抽出された%s数: %d", 
            extraction_config.result_name.replace('_defs', ''), 
            len(element_defs)
        )
        
        # 7. 結果を返す
        return element_defs
    
    def _find_stb_members(self) -> Optional:
        """StbMembersコンテナを検索"""
        stb_members_element = self.xml_parser.find_element(".//stb:StbMembers")
        if stb_members_element is None:
            logger.warning("StbMembers 要素が見つかりません")
        return stb_members_element
    
    def _extract_from_container(
        self,
        stb_members_element,
        container_config: ContainerConfig,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        namespaces: Dict[str, str]
    ) -> List[Dict]:
        """指定されたコンテナから要素を抽出"""
        elements = []
        
        # コンテナ要素を検索
        container_element = stb_members_element.find(
            f".//stb:{container_config.container_tag}", namespaces
        )
        
        if container_element is None:
            logger.info(f"{container_config.container_tag} 要素が見つかりません")
            return elements
        
        # 個別要素を処理
        for element_elem in container_element.findall(
            f"stb:{container_config.element_tag}", namespaces
        ):
            element_result = self._extract_single_element(
                element_elem, 
                nodes_data, 
                sections_data, 
                node_story_map,
                container_config.element_type
            )
            if element_result:
                # 結果が単一の辞書かリストかを判定
                if isinstance(element_result, list):
                    elements.extend(element_result)
                else:
                    elements.append(element_result)
        
        return elements
    
    @abstractmethod
    def _extract_single_element(
        self,
        element_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ):
        """単一要素の抽出処理（サブクラスで実装）
        
        Args:
            element_elem: 要素のXML要素
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書
            node_story_map: ノード-階層マッピング
            element_type: 要素タイプ（StbGirder, StbColumn等）
            
        Returns:
            抽出された要素定義（Dict）、要素定義のリスト（List[Dict]）、
            または失敗時はNone
        """
        pass


class STBExtractionConfigs:
    """ST-Bridge要素の抽出設定定義"""
    
    @staticmethod
    def get_beam_config() -> ExtractionConfig:
        """梁の抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbGirders", "StbGirder", "StbGirder"),
                ContainerConfig("StbBeams", "StbBeam", "StbBeam")
            ],
            result_name="beam_defs"
        )
    
    @staticmethod
    def get_column_config() -> ExtractionConfig:
        """柱の抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbColumns", "StbColumn", "StbColumn"),
                ContainerConfig("StbPosts", "StbPost", "StbPost")
            ],
            result_name="column_defs"
        )
    
    @staticmethod
    def get_wall_config() -> ExtractionConfig:
        """壁の抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbWalls", "StbWall", "StbWall")
            ],
            result_name="wall_defs"
        )
    
    @staticmethod
    def get_slab_config() -> ExtractionConfig:
        """スラブの抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbSlabs", "StbSlab", "StbSlab")
            ],
            result_name="slab_defs"
        )
    
    @staticmethod
    def get_brace_config() -> ExtractionConfig:
        """ブレースの抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbBraces", "StbBrace", "StbBrace")
            ],
            result_name="brace_defs"
        )
    
    @staticmethod
    def get_foundation_column_config() -> ExtractionConfig:
        """基礎柱の抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbFoundationColumns", "StbFoundationColumn", "StbFoundationColumn")
            ],
            result_name="foundation_column_defs"
        )
    
    @staticmethod
    def get_footing_config() -> ExtractionConfig:
        """フーチングの抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbFootings", "StbFooting", "StbFooting")
            ],
            result_name="footing_defs"
        )
    
    @staticmethod
    def get_pile_config() -> ExtractionConfig:
        """杭の抽出設定"""
        return ExtractionConfig(
            containers=[
                ContainerConfig("StbPiles", "StbPile", "StbPile")
            ],
            result_name="pile_defs"
        )