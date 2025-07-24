"""
ElementCentricIntegrationService - 要素中心アプローチ統合サービス
既存システムとの互換性を保ちながら新アプローチを段階的に導入
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time
from utils.logger import get_logger
from exceptions.custom_errors import ConversionError

# 既存コンポーネントのインポート
from .element_story_analyzer import ElementStoryAnalyzer
from .element_centric_converter import ElementCentricConverter, ConversionResult
from .story_element_relationship_manager import StoryElementRelationshipManager

# 既存システムのインポート
from ifcCreator.core.element_creation_factory import ElementCreationFactory
from ifcCreator.core.ifc_project_builder import IFCProjectBuilder
from ifcCreator.core.story_converter import StbToIfcStoryConverter


class ConversionMode(Enum):
    """変換モード"""
    LEGACY = "legacy"              # 従来の階層中心アプローチ
    ELEMENT_CENTRIC = "element_centric"  # 新しい要素中心アプローチ
    HYBRID = "hybrid"              # ハイブリッドモード（フォールバック機能付き）
    AUTO = "auto"                  # 自動選択モード


@dataclass
class IntegrationConfig:
    """統合設定"""
    conversion_mode: ConversionMode = ConversionMode.HYBRID
    enable_fallback: bool = True
    enable_performance_comparison: bool = True
    fallback_threshold_ms: float = 5000.0  # フォールバック閾値（5秒）
    duplicate_tolerance: int = 0  # 許容重複数
    confidence_threshold: float = 0.7  # 信頼度閾値
    enable_detailed_logging: bool = True


@dataclass
class ComparisonResult:
    """パフォーマンス比較結果"""
    legacy_time_ms: float
    element_centric_time_ms: float
    legacy_element_count: int
    element_centric_element_count: int
    legacy_duplicate_count: int
    element_centric_duplicate_count: int
    performance_improvement: float  # パーセンテージ
    recommendation: ConversionMode


class ElementCentricIntegrationService:
    """
    要素中心アプローチの統合サービス
    
    機能:
    - 新旧アプローチの統合インターフェース
    - 段階的移行のサポート
    - フォールバック機能
    - パフォーマンス比較
    - 設定ベースの動作切り替え
    """
    
    def __init__(
        self,
        config: IntegrationConfig = None,
        logger=None
    ):
        self.config = config or IntegrationConfig()
        self.logger = logger or get_logger(__name__)
        
        # 統計情報
        self.conversion_history = []
        self.fallback_count = 0
        self.performance_data = []
        
        self.logger.info("ElementCentricIntegrationService初期化完了 - モード: %s", 
                        self.config.conversion_mode.value)
    
    def convert_with_integration(
        self,
        story_defs: List[Dict],
        element_defs: Dict[str, List[Dict]],
        node_story_map: Dict[str, str],
        project_builder: IFCProjectBuilder,
        axes_defs: List[Dict] = None
    ) -> ConversionResult:
        """
        統合された変換処理を実行
        
        Args:
            story_defs: 階層定義リスト
            element_defs: 要素定義辞書
            node_story_map: ノード-階層マッピング
            project_builder: IFCプロジェクトビルダー
            axes_defs: 軸定義リスト（オプション）
            
        Returns:
            ConversionResult: 統合変換結果
        """
        start_time = time.time()
        
        try:
            # 変換モードに基づく処理分岐
            if self.config.conversion_mode == ConversionMode.LEGACY:
                return self._execute_legacy_conversion(
                    story_defs, element_defs, node_story_map, project_builder, axes_defs
                )
            
            elif self.config.conversion_mode == ConversionMode.ELEMENT_CENTRIC:
                return self._execute_element_centric_conversion(
                    story_defs, element_defs, node_story_map, project_builder, axes_defs
                )
            
            elif self.config.conversion_mode == ConversionMode.HYBRID:
                return self._execute_hybrid_conversion(
                    story_defs, element_defs, node_story_map, project_builder, axes_defs
                )
            
            elif self.config.conversion_mode == ConversionMode.AUTO:
                return self._execute_auto_conversion(
                    story_defs, element_defs, node_story_map, project_builder, axes_defs
                )
            
            else:
                raise ConversionError(f"未対応の変換モード: {self.config.conversion_mode}")
                
        except Exception as e:
            error_msg = f"統合変換エラー: {str(e)}"
            self.logger.error(error_msg)
            
            # エラー時のフォールバック
            if self.config.enable_fallback and self.config.conversion_mode != ConversionMode.LEGACY:
                self.logger.warning("フォールバックを実行します")
                self.fallback_count += 1
                return self._execute_legacy_conversion(
                    story_defs, element_defs, node_story_map, project_builder, axes_defs
                )
            
            raise ConversionError(error_msg) from e
        
        finally:
            processing_time = (time.time() - start_time) * 1000
            self.conversion_history.append({
                'mode': self.config.conversion_mode.value,
                'processing_time_ms': processing_time,
                'timestamp': time.time(),
                'element_count': sum(len(elements) for elements in element_defs.values())
            })
    
    def _execute_legacy_conversion(
        self,
        story_defs: List[Dict],
        element_defs: Dict[str, List[Dict]],
        node_story_map: Dict[str, str],
        project_builder: IFCProjectBuilder,
        axes_defs: List[Dict] = None
    ) -> ConversionResult:
        """従来の階層中心アプローチで変換実行"""
        self.logger.info("従来アプローチで変換実行")
        
        start_time = time.time()
        
        try:
            # 既存のStbToIfcStoryConverterを使用
            story_converter = StbToIfcStoryConverter(project_builder)
            
            # 既存の変換処理を実行
            story_converter.convert_stb_stories_to_ifc_stories(
                story_defs, element_defs, node_story_map, axes_defs
            )
            
            # 結果を新形式に変換
            processing_time = (time.time() - start_time) * 1000
            
            return self._create_legacy_conversion_result(
                story_converter, processing_time
            )
            
        except Exception as e:
            self.logger.error("従来アプローチ変換エラー: %s", str(e))
            raise ConversionError(f"従来アプローチ変換失敗: {str(e)}") from e
    
    def _execute_element_centric_conversion(
        self,
        story_defs: List[Dict],
        element_defs: Dict[str, List[Dict]],
        node_story_map: Dict[str, str],
        project_builder: IFCProjectBuilder,
        axes_defs: List[Dict] = None
    ) -> ConversionResult:
        """要素中心アプローチで変換実行"""
        self.logger.info("要素中心アプローチで変換実行")
        
        try:
            # 新コンポーネントを初期化
            analyzer = ElementStoryAnalyzer(node_story_map)
            factory = ElementCreationFactory(project_builder)
            relationship_manager = StoryElementRelationshipManager(project_builder)
            
            converter = ElementCentricConverter(analyzer, factory, relationship_manager)
            
            # 軸の処理（既存システムを使用）
            if axes_defs:
                self._process_axes_with_legacy(axes_defs, project_builder)
            
            # 要素中心変換実行
            result = converter.convert_all_elements(story_defs, element_defs)
            
            self.logger.info("要素中心変換完了 - 作成要素数: %d, 処理時間: %.2fms",
                            result.statistics.created_elements,
                            result.statistics.processing_time_ms)
            
            return result
            
        except Exception as e:
            self.logger.error("要素中心アプローチ変換エラー: %s", str(e))
            raise ConversionError(f"要素中心アプローチ変換失敗: {str(e)}") from e
    
    def _execute_hybrid_conversion(
        self,
        story_defs: List[Dict],
        element_defs: Dict[str, List[Dict]],
        node_story_map: Dict[str, str],
        project_builder: IFCProjectBuilder,
        axes_defs: List[Dict] = None
    ) -> ConversionResult:
        """
        ハイブリッドモード変換実行（フォールバック機能付き）
        
        Debug Notes:
            - 要素中心アプローチを優先実行
            - 品質チェック失敗時に従来アプローチにフォールバック
            - フォールバック回数をカウントして統計記録
        """
        self.logger.info("ハイブリッドモードで変換実行")
        
        # DEBUG: ハイブリッドモード開始時の状態ログ
        total_elements = sum(len(elements) for elements in element_defs.values())
        self.logger.debug("DEBUG: ハイブリッドモード - 総要素数: %d, 階層数: %d", 
                         total_elements, len(story_defs))
        
        try:
            # まず要素中心アプローチを試行
            self.logger.debug("DEBUG: 要素中心アプローチ試行開始")
            start_time = time.time()
            
            result = self._execute_element_centric_conversion(
                story_defs, element_defs, node_story_map, project_builder, axes_defs
            )
            
            element_centric_time = (time.time() - start_time) * 1000
            self.logger.debug("DEBUG: 要素中心アプローチ処理時間: %.2fms", element_centric_time)
            
            # 品質チェック
            if self._validate_conversion_quality(result):
                self.logger.info("要素中心アプローチ成功 - 品質基準をクリア")
                return result
            else:
                self.logger.warning("WARNING: 要素中心アプローチの品質が基準以下 - フォールバック実行")
                self.logger.debug("DEBUG: 品質チェック詳細 - 失敗要素: %d, 重複要素: %d", 
                                result.statistics.failed_elements, 
                                result.statistics.duplicate_elements)
                self.fallback_count += 1
                
                # フォールバック実行
                self.logger.debug("DEBUG: 従来アプローチによるフォールバック開始")
                fallback_start = time.time()
                
                fallback_result = self._execute_legacy_conversion(
                    story_defs, element_defs, node_story_map, project_builder, axes_defs
                )
                
                fallback_time = (time.time() - fallback_start) * 1000
                self.logger.info("フォールバック完了 - 処理時間: %.2fms", fallback_time)
                
                return fallback_result
                
        except Exception as e:
            self.logger.warning("WARNING: 要素中心アプローチで例外発生 - フォールバック実行: %s", str(e))
            self.logger.debug("DEBUG: 例外詳細", exc_info=True)
            self.fallback_count += 1
            
            # 例外時のフォールバック実行
            try:
                self.logger.debug("DEBUG: 例外時フォールバック開始")
                return self._execute_legacy_conversion(
                    story_defs, element_defs, node_story_map, project_builder, axes_defs
                )
            except Exception as fallback_error:
                self.logger.error("ERROR: フォールバックも失敗: %s", str(fallback_error))
                raise ConversionError(
                    f"要素中心アプローチとフォールバック両方が失敗: {str(e)}, {str(fallback_error)}"
                ) from e
    
    def _execute_auto_conversion(
        self,
        story_defs: List[Dict],
        element_defs: Dict[str, List[Dict]],
        node_story_map: Dict[str, str],
        project_builder: IFCProjectBuilder,
        axes_defs: List[Dict] = None
    ) -> ConversionResult:
        """自動選択モード変換実行"""
        self.logger.info("自動選択モードで変換実行")
        
        # データ規模に基づく自動判定
        total_elements = sum(len(elements) for elements in element_defs.values())
        story_count = len(story_defs)
        
        # 判定ロジック
        if total_elements > 1000 or story_count > 10:
            # 大規模データは要素中心アプローチが有利
            selected_mode = ConversionMode.ELEMENT_CENTRIC
        elif total_elements < 100 and story_count < 3:
            # 小規模データは従来アプローチでも十分
            selected_mode = ConversionMode.LEGACY
        else:
            # 中規模データはハイブリッドモード
            selected_mode = ConversionMode.HYBRID
        
        self.logger.info("自動選択結果: %s (要素数: %d, 階層数: %d)", 
                        selected_mode.value, total_elements, story_count)
        
        # 選択されたモードで実行
        original_mode = self.config.conversion_mode
        self.config.conversion_mode = selected_mode
        
        try:
            return self.convert_with_integration(
                story_defs, element_defs, node_story_map, project_builder, axes_defs
            )
        finally:
            self.config.conversion_mode = original_mode
    
    def compare_performance(
        self,
        story_defs: List[Dict],
        element_defs: Dict[str, List[Dict]],
        node_story_map: Dict[str, str],
        project_builder: IFCProjectBuilder
    ) -> ComparisonResult:
        """パフォーマンス比較を実行"""
        self.logger.info("パフォーマンス比較開始")
        
        # 従来アプローチで実行
        legacy_start = time.time()
        legacy_result = self._execute_legacy_conversion(
            story_defs, element_defs, node_story_map, project_builder
        )
        legacy_time = (time.time() - legacy_start) * 1000
        
        # 要素中心アプローチで実行  
        element_start = time.time()
        element_result = self._execute_element_centric_conversion(
            story_defs, element_defs, node_story_map, project_builder
        )
        element_time = (time.time() - element_start) * 1000
        
        # 比較結果作成
        performance_improvement = ((legacy_time - element_time) / legacy_time) * 100
        
        # 推奨モード判定
        if performance_improvement > 30 and element_result.statistics.duplicate_elements == 0:
            recommendation = ConversionMode.ELEMENT_CENTRIC
        elif performance_improvement > 10:
            recommendation = ConversionMode.HYBRID
        else:
            recommendation = ConversionMode.LEGACY
        
        comparison = ComparisonResult(
            legacy_time_ms=legacy_time,
            element_centric_time_ms=element_time,
            legacy_element_count=len(legacy_result.created_elements),
            element_centric_element_count=element_result.statistics.created_elements,
            legacy_duplicate_count=0,  # 従来は重複カウント困難
            element_centric_duplicate_count=element_result.statistics.duplicate_elements,
            performance_improvement=performance_improvement,
            recommendation=recommendation
        )
        
        self.performance_data.append(comparison)
        
        self.logger.info("パフォーマンス比較完了 - 改善率: %.1f%%, 推奨モード: %s",
                        performance_improvement, recommendation.value)
        
        return comparison
    
    def _validate_conversion_quality(self, result: ConversionResult) -> bool:
        """変換品質の検証"""
        # 基本的な品質チェック
        if result.statistics.failed_elements > 0:
            return False
        
        # 重複チェック
        if result.statistics.duplicate_elements > self.config.duplicate_tolerance:
            return False
        
        # 信頼度チェック（要素中心アプローチ固有）
        if hasattr(result.statistics, 'analysis_method_counts'):
            low_confidence_count = result.statistics.analysis_method_counts.get('coordinates', 0)
            total_elements = result.statistics.created_elements
            
            if total_elements > 0:
                low_confidence_ratio = low_confidence_count / total_elements
                if low_confidence_ratio > (1.0 - self.config.confidence_threshold):
                    return False
        
        return True
    
    def _process_axes_with_legacy(self, axes_defs: List[Dict], project_builder: IFCProjectBuilder):
        """軸の処理（既存システム使用）"""
        # 既存のStbToIfcStoryConverterの軸処理機能を使用
        try:
            story_converter = StbToIfcStoryConverter(project_builder)
            story_converter._convert_grid_axes(project_builder, axes_defs)
        except Exception as e:
            self.logger.warning("軸処理エラー: %s", str(e))
    
    def _create_legacy_conversion_result(
        self, 
        story_converter: StbToIfcStoryConverter,
        processing_time: float
    ) -> ConversionResult:
        """従来変換結果を新形式に変換"""
        # 従来システムから統計情報を抽出
        # 注意: 実際の実装は既存システムの仕様に依存
        
        from .element_centric_converter import ConversionStatistics
        
        statistics = ConversionStatistics(
            processing_time_ms=processing_time,
            created_elements=0,  # 従来システムから取得困難
            total_elements=0,
            duplicate_elements=0,  # 従来システムでは正確な計測困難
        )
        
        return ConversionResult(
            created_elements=[],  # 従来システムからの変換は複雑
            created_stories={},
            spatial_relationships=[],
            statistics=statistics,
            errors=[],
            warnings=[]
        )
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """統合統計情報の取得"""
        return {
            'total_conversions': len(self.conversion_history),
            'fallback_count': self.fallback_count,
            'fallback_rate': self.fallback_count / len(self.conversion_history) if self.conversion_history else 0,
            'average_processing_time': sum(h['processing_time_ms'] for h in self.conversion_history) / len(self.conversion_history) if self.conversion_history else 0,
            'mode_usage': {mode.value: sum(1 for h in self.conversion_history if h['mode'] == mode.value) for mode in ConversionMode},
            'performance_improvements': [p.performance_improvement for p in self.performance_data]
        }