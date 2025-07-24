"""
ElementCentricConverter - 要素中心アプローチによる変換処理管理クラス
階層に依存しない要素作成と効率的な重複排除を実現
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import time
import hashlib
import logging
from utils.logger import get_logger
from exceptions.custom_errors import ConversionError
from .element_story_analyzer import ElementStoryAnalyzer, StoryAnalysisResult


@dataclass
class ElementInfo:
    """作成要素の情報を格納するデータクラス"""
    element_id: str
    element_type: str
    ifc_element: Any
    story_name: str
    definition: Dict[str, Any]
    created_at: datetime
    coordinates: Optional[tuple[float, float, float]] = None
    section_name: Optional[str] = None
    analysis_method: Optional[str] = None
    confidence: float = 1.0


@dataclass
class ConversionStatistics:
    """変換統計情報"""
    total_elements: int = 0
    created_elements: int = 0
    duplicate_elements: int = 0
    failed_elements: int = 0
    processing_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    element_type_counts: Dict[str, int] = field(default_factory=dict)
    analysis_method_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class ConversionResult:
    """変換結果を格納するデータクラス"""
    created_elements: List[ElementInfo]
    created_stories: Dict[str, Any]
    spatial_relationships: List[Any]
    statistics: ConversionStatistics
    errors: List[str]
    warnings: List[str]


class ElementCentricConverter:
    """
    要素中心アプローチによる変換処理管理クラス
    
    特徴:
    - 階層に依存しない要素作成
    - 3段階の重複排除機構
    - 統計情報とパフォーマンス監視
    - 詳細なエラーハンドリング
    """
    
    def __init__(
        self,
        story_analyzer: ElementStoryAnalyzer,
        element_factory,  # ElementCreationFactory
        relationship_manager=None  # StoryElementRelationshipManager
    ):
        """
        Args:
            story_analyzer: 階層分析器
            element_factory: 要素作成ファクトリー
            relationship_manager: 関係管理器（オプション）
        """
        self.story_analyzer = story_analyzer
        self.element_factory = element_factory
        self.relationship_manager = relationship_manager
        self.logger = get_logger(__name__)
        
        # 重複排除用のレジストリ
        self.created_elements_registry: Dict[str, ElementInfo] = {}
        self.element_id_set: Set[str] = set()
        self.element_name_set: Set[str] = set()
        self.element_hash_set: Set[str] = set()
        
        # 統計情報
        self.statistics = ConversionStatistics()
        self.conversion_start_time = 0.0
        
        self.logger.info("ElementCentricConverter初期化完了")
    
    def convert_all_elements(
        self, 
        story_defs: List[Dict], 
        element_defs: Dict[str, List[Dict]]
    ) -> ConversionResult:
        """
        要素中心アプローチによる全変換処理
        
        Args:
            story_defs: 階層定義リスト
            element_defs: 要素定義辞書 {element_type: [definition, ...]}
            
        Returns:
            ConversionResult: 変換結果オブジェクト
        """
        self.conversion_start_time = time.time()
        self.logger.info("要素中心変換開始 - 階層数: %d, 要素タイプ数: %d", 
                        len(story_defs), len(element_defs))
        
        errors = []
        warnings = []
        created_stories = {}
        
        try:
            # Step 1: 階層標高情報を準備
            story_elevations = self._prepare_story_elevations(story_defs)
            
            # Step 2: 全要素の階層関係を一括分析
            self.logger.info("全要素階層分析開始")
            analyzed_elements = self.story_analyzer.batch_analyze_elements(
                element_defs, story_elevations
            )
            
            # Step 3: 重複排除 & 要素作成
            self.logger.info("要素作成開始")
            created_elements = self.create_elements_with_story_info(analyzed_elements)
            
            # Step 4: 空間関係の設定（関係管理器が設定されている場合）
            spatial_relationships = []
            if self.relationship_manager:
                self.logger.info("空間関係設定開始")
                spatial_relationships = self._create_spatial_relationships(
                    created_elements, story_defs
                )
            
            # Step 5: 統計計算
            self._calculate_final_statistics(created_elements)
            
            return ConversionResult(
                created_elements=created_elements,
                created_stories=created_stories,
                spatial_relationships=spatial_relationships,
                statistics=self.statistics,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"要素中心変換エラー: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            return ConversionResult(
                created_elements=[],
                created_stories={},
                spatial_relationships=[],
                statistics=self.statistics,
                errors=errors,
                warnings=warnings
            )
    
    def create_elements_with_story_info(
        self, 
        analyzed_elements: Dict[str, Dict[str, List[Dict]]]
    ) -> List[ElementInfo]:
        """
        階層情報付きで要素を作成
        
        Args:
            analyzed_elements: 階層分析済み要素群
            {story_name: {element_type: [element_def, ...]}}
            
        Returns:
            List[ElementInfo]: 作成要素情報リスト
        """
        all_created_elements = []
        total_elements = sum(
            len(elements) 
            for story_elements in analyzed_elements.values() 
            for elements in story_elements.values()
        )
        
        self.statistics.total_elements = total_elements
        self.logger.info("要素作成開始 - 総要素数: %d", total_elements)
        
        # 階層別・要素タイプ別に処理
        for story_name, story_elements in analyzed_elements.items():
            self.logger.debug("階層 %s の要素作成開始", story_name)
            
            for element_type, element_defs in story_elements.items():
                if not element_defs:
                    continue
                
                self.logger.debug("要素タイプ %s: %d個", element_type, len(element_defs))
                
                # 重複排除
                unique_elements = self._ensure_no_duplicates(element_defs)
                self.statistics.duplicate_elements += len(element_defs) - len(unique_elements)
                
                # 要素作成実行
                created_elements = self._create_elements_batch(
                    unique_elements, element_type, story_name
                )
                
                all_created_elements.extend(created_elements)
                
                # 統計更新
                if element_type not in self.statistics.element_type_counts:
                    self.statistics.element_type_counts[element_type] = 0
                self.statistics.element_type_counts[element_type] += len(created_elements)
        
        self.statistics.created_elements = len(all_created_elements)
        self.logger.info("要素作成完了 - 作成数: %d, 重複排除数: %d", 
                        len(all_created_elements), self.statistics.duplicate_elements)
        
        return all_created_elements
    
    def _ensure_no_duplicates(self, element_defs: List[Dict]) -> List[Dict]:
        """
        3段階の重複排除を実行
        1. ID重複チェック
        2. 名前重複チェック  
        3. ハッシュ重複チェック（位置・セクション）
        
        Debug Notes:
            - ID重複: 同一要素の完全重複を検出
            - 名前重複: セクション名による重複を検出
            - ハッシュ重複: 位置・形状による実質的重複を検出
        """
        unique_elements = []
        duplicate_count_by_stage = {'id': 0, 'name': 0, 'hash': 0}
        
        # DEBUG: 重複チェック開始ログ
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("DEBUG: 重複チェック開始 - 対象要素数: %d", len(element_defs))
            self.logger.debug("DEBUG: 既存ID数: %d, 既存名前数: %d, 既存ハッシュ数: %d", 
                            len(self.element_id_set), 
                            len(self.element_name_set), 
                            len(self.element_hash_set))
        
        for i, element_def in enumerate(element_defs):
            element_id = element_def.get('id', f'no_id_{i}')
            
            # Stage 1: ID重複チェック
            if element_id and element_id in self.element_id_set:
                self.logger.debug("DEBUG: ID重複スキップ - ID: %s", element_id)
                duplicate_count_by_stage['id'] += 1
                continue
            
            # Stage 2: 名前重複チェック
            element_name = self._get_element_name(element_def)
            if element_name and element_name in self.element_name_set:
                self.logger.debug("DEBUG: 名前重複スキップ - 名前: %s (ID: %s)", element_name, element_id)
                duplicate_count_by_stage['name'] += 1
                continue
            
            # Stage 3: ハッシュ重複チェック（位置・セクション）
            element_hash = self._calculate_element_hash(element_def)
            if element_hash in self.element_hash_set:
                self.logger.debug("DEBUG: ハッシュ重複スキップ - ハッシュ: %s (ID: %s)", 
                                element_hash[:8], element_id)
                duplicate_count_by_stage['hash'] += 1
                continue
            
            # 重複なし - 追加
            if element_id:
                self.element_id_set.add(element_id)
            if element_name:
                self.element_name_set.add(element_name)
            self.element_hash_set.add(element_hash)
            
            unique_elements.append(element_def)
        
        # DEBUG: 重複チェック結果ログ
        total_duplicates = sum(duplicate_count_by_stage.values())
        if total_duplicates > 0:
            self.logger.info("重複排除結果 - ID: %d, 名前: %d, ハッシュ: %d (総重複: %d)", 
                           duplicate_count_by_stage['id'],
                           duplicate_count_by_stage['name'], 
                           duplicate_count_by_stage['hash'],
                           total_duplicates)
        
        return unique_elements
    
    def _create_elements_batch(
        self, 
        element_defs: List[Dict], 
        element_type: str, 
        story_name: str
    ) -> List[ElementInfo]:
        """要素の一括作成"""
        created_elements = []
        
        for element_def in element_defs:
            try:
                # 要素作成実行
                ifc_element = self._create_single_element(element_def, element_type)
                
                if ifc_element:
                    # ElementInfo作成
                    element_info = ElementInfo(
                        element_id=element_def.get('id', f"{element_type}_{len(created_elements)}"),
                        element_type=element_type,
                        ifc_element=ifc_element,
                        story_name=story_name,
                        definition=element_def,
                        created_at=datetime.now(),
                        section_name=self._get_element_name(element_def),
                        analysis_method=element_def.get('analysis_method'),
                        confidence=element_def.get('analysis_confidence', 1.0)
                    )
                    
                    created_elements.append(element_info)
                    self.created_elements_registry[element_info.element_id] = element_info
                    
                    # 分析手法統計更新
                    method = element_def.get('analysis_method', 'unknown')
                    if method not in self.statistics.analysis_method_counts:
                        self.statistics.analysis_method_counts[method] = 0
                    self.statistics.analysis_method_counts[method] += 1
                
            except Exception as e:
                self.logger.warning("要素作成失敗 %s: %s", 
                                  element_def.get('id', 'unknown'), str(e))
                self.statistics.failed_elements += 1
        
        return created_elements
    
    def _create_single_element(self, element_def: Dict, element_type: str) -> Any:
        """単一要素の作成"""
        # ElementCreationFactoryを使用
        creator = self.element_factory.get_creator(element_type)
        if not creator:
            raise ConversionError(f"未対応要素タイプ: {element_type}")
        
        return creator.create_element(element_def)
    
    def _get_element_name(self, element_def: Dict) -> Optional[str]:
        """要素名を取得"""
        name_keys = ['name', 'stb_section_name', 'section_name', 'id']
        for key in name_keys:
            if key in element_def and element_def[key]:
                return str(element_def[key])
        return None
    
    def _calculate_element_hash(self, element_def: Dict) -> str:
        """要素のハッシュ値を計算（位置・セクション情報ベース）"""
        hash_components = []
        
        # 位置情報
        for key in ['start_point', 'end_point', 'center_point', 'coordinates']:
            if key in element_def:
                hash_components.append(str(element_def[key]))
        
        # セクション情報
        for key in ['section_name', 'stb_section_name', 'section_id']:
            if key in element_def:
                hash_components.append(str(element_def[key]))
        
        # ノード情報
        for key in ['start_node_id', 'end_node_id', 'node_ids']:
            if key in element_def:
                hash_components.append(str(element_def[key]))
        
        hash_string = '|'.join(hash_components)
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    def _prepare_story_elevations(self, story_defs: List[Dict]) -> Dict[str, tuple[float, float]]:
        """階層標高情報を準備"""
        story_elevations = {}
        
        for story_def in story_defs:
            story_name = story_def.get('name', story_def.get('id'))
            elevation = float(story_def.get('elevation', 0.0))
            height = float(story_def.get('height', 3000.0))  # デフォルト3m
            
            base_z = elevation
            top_z = elevation + height
            
            story_elevations[story_name] = (base_z, top_z)
        
        return story_elevations
    
    def _create_spatial_relationships(
        self, 
        created_elements: List[ElementInfo], 
        story_defs: List[Dict]
    ) -> List[Any]:
        """空間関係の作成（関係管理器使用）"""
        if not self.relationship_manager:
            return []
        
        # 要素を階層別にグループ化
        for element_info in created_elements:
            self.relationship_manager.register_element_to_story(
                element_info, element_info.story_name
            )
        
        return self.relationship_manager.create_spatial_relationships()
    
    def _calculate_final_statistics(self, created_elements: List[ElementInfo]) -> None:
        """最終統計の計算"""
        end_time = time.time()
        self.statistics.processing_time_ms = (end_time - self.conversion_start_time) * 1000
        
        # 信頼度別統計
        confidence_stats = {}
        for element in created_elements:
            confidence = element.confidence
            if confidence not in confidence_stats:
                confidence_stats[confidence] = 0
            confidence_stats[confidence] += 1
        
        self.logger.info("変換統計 - 作成数: %d, 重複: %d, 失敗: %d, 処理時間: %.2fms",
                        self.statistics.created_elements,
                        self.statistics.duplicate_elements,
                        self.statistics.failed_elements,
                        self.statistics.processing_time_ms)
    
    def get_conversion_statistics(self) -> ConversionStatistics:
        """変換統計情報の取得"""
        return self.statistics
    
    def validate_element_integrity(self, elements: List[ElementInfo]) -> bool:
        """要素整合性の検証"""
        # 基本的な整合性チェック
        for element in elements:
            if not element.element_id or not element.ifc_element:
                self.logger.warning("要素整合性エラー: %s", element.element_id)
                return False
        
        # 重複チェック
        element_ids = [e.element_id for e in elements]
        if len(element_ids) != len(set(element_ids)):
            self.logger.warning("要素ID重複検出")
            return False
        
        return True