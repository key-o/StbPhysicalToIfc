"""
ElementStoryAnalyzer - 要素の階層所属を分析・決定する専門クラス
要素中心アプローチの核となるコンポーネント
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from utils.logger import get_logger
from exceptions.custom_errors import ConversionError


@dataclass
class StoryAnalysisResult:
    """階層分析結果を格納するデータクラス"""
    story_name: str
    confidence: float  # 判定の信頼度 (0.0-1.0)
    analysis_method: str  # 'floor_attribute', 'node_ids', 'coordinates'
    coordinates: Optional[Tuple[float, float, float]] = None
    node_ids: Optional[List[str]] = None


class ElementStoryAnalyzer:
    """
    要素の階層所属を分析・決定するクラス
    
    3段階の判定アルゴリズム：
    1. floor属性による判定（最優先、信頼度1.0）
    2. node_idsによる判定（信頼度0.8）
    3. 座標による判定（最終手段、信頼度0.6）
    """
    
    def __init__(self, node_story_map: Dict[str, str], logger=None):
        """
        要素階層分析器の初期化
        
        Args:
            node_story_map: ノードIDから階層名へのマッピング
            logger: ログ出力用ロガー
        
        Debug Notes:
            - node_story_mapが空の場合、node_ids判定は全て失敗する
            - story_elevationsが未設定の場合、座標判定は全て失敗する
        """
        self.node_story_map = node_story_map
        self.logger = logger or get_logger(__name__)
        self.story_elevations = {}  # {story_name: (base_z, top_z)}
        
        # DEBUG: ノードマップの統計情報をログ出力
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("DEBUG: ノードマップ統計 - 総ノード数: %d", len(node_story_map))
            if node_story_map:
                story_counts = {}
                for story in node_story_map.values():
                    story_counts[story] = story_counts.get(story, 0) + 1
                self.logger.debug("DEBUG: 階層別ノード数: %s", story_counts)
        
        # 要素タイプ別の代表ノード取得戦略
        self.node_selection_strategy = {
            'beam': ['start_node_id'],
            'girder': ['start_node_id'],
            'brace': ['start_node_id'],
            'column': ['bottom_node_id'],
            'pile': ['bottom_node_id'], 
            'foundation_column': ['bottom_node_id'],
            'wall': ['node_ids[0]', 'primary_node_id'],
            'slab': ['node_ids[0]', 'primary_node_id'],
            'footing': ['node_ids[0]', 'primary_node_id']
        }
        
        self.logger.info("ElementStoryAnalyzer初期化完了 - ノードマップ: %d件", 
                        len(self.node_story_map))
    
    def set_story_elevations(self, story_elevations: Dict[str, Tuple[float, float]]) -> None:
        """
        階層標高情報を設定
        
        Args:
            story_elevations: {story_name: (base_z, top_z)}の辞書
        """
        self.story_elevations = story_elevations
        self.logger.info("階層標高情報設定完了 - %d階層", len(story_elevations))
    
    def analyze_element_story_relationship(
        self, 
        element_def: Dict[str, Any], 
        element_type: str
    ) -> StoryAnalysisResult:
        """
        要素の所属階層を決定（3段階判定アルゴリズム）
        
        Args:
            element_def: 要素定義辞書
            element_type: 要素タイプ('beam', 'column', etc.)
            
        Returns:
            StoryAnalysisResult: 分析結果
            
        Raises:
            ConversionError: 階層判定に失敗した場合
            
        Debug Notes:
            - Stage 1 (floor属性): 信頼度1.0、最優先
            - Stage 2 (node_ids): 信頼度0.8、フォールバック
            - Stage 3 (座標): 信頼度0.6、最終手段
        """
        element_id = element_def.get('id', 'unknown')
        
        # DEBUG: 要素分析開始のログ
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("DEBUG: 要素階層分析開始 - ID: %s, タイプ: %s", 
                           element_id, element_type)
            available_keys = list(element_def.keys())
            self.logger.debug("DEBUG: 利用可能な判定キー: %s", available_keys)
        
        try:
            # Stage 1: floor属性による判定（最優先）
            result = self._analyze_by_floor_attribute(element_def)
            if result:
                self.logger.debug("要素%s: floor属性による判定成功 - %s (信頼度: %.1f)", 
                               element_id, result.story_name, result.confidence)
                return result
            else:
                self.logger.debug("DEBUG: floor属性判定失敗 - floor属性なし")
            
            # Stage 2: node_idsによる判定
            result = self._analyze_by_node_ids(element_def, element_type)
            if result:
                self.logger.debug("要素%s: node_ids判定成功 - %s (信頼度: %.1f)", 
                               element_id, result.story_name, result.confidence)
                return result
            else:
                self.logger.debug("DEBUG: node_ids判定失敗 - ノード情報不足")
            
            # Stage 3: 座標による判定（最終手段）
            result = self._analyze_by_coordinates(element_def, element_type)
            if result:
                self.logger.debug("要素%s: 座標判定成功 - %s (信頼度: %.1f)", 
                               element_id, result.story_name, result.confidence)
                return result
            else:
                self.logger.debug("DEBUG: 座標判定失敗 - 座標情報不足または階層標高未設定")
            
            # すべての判定が失敗
            error_msg = f"要素{element_id}({element_type})の階層判定に失敗 - 3段階すべて失敗"
            self.logger.warning("WARNING: %s", error_msg)
            raise ConversionError(error_msg)
            
        except ConversionError:
            # 既知のエラーはそのまま再発生
            raise
        except Exception as e:
            self.logger.error("ERROR: 要素%s の階層分析中に予期しないエラー: %s", element_id, str(e))
            raise ConversionError(
                f"要素{element_id}の階層分析エラー: {str(e)}"
            ) from e
    
    def batch_analyze_elements(
        self, 
        element_defs: Dict[str, List[Dict]], 
        story_elevations: Dict[str, Tuple[float, float]]
    ) -> Dict[str, Dict[str, List[Dict]]]:
        """
        全要素の階層関係を一括分析
        
        Args:
            element_defs: {element_type: [element_def, ...]}
            story_elevations: {story_name: (base_z, top_z)}
            
        Returns:
            Dict[str, Dict[str, List[Dict]]]: 
            {story_name: {element_type: [element_def, ...]}}
        """
        self.set_story_elevations(story_elevations)
        
        # 階層別要素辞書を初期化
        analyzed_elements = {}
        total_elements = sum(len(elements) for elements in element_defs.values())
        processed_elements = 0
        
        self.logger.info("一括要素分析開始 - 総要素数: %d", total_elements)
        
        # 各要素タイプを処理
        for element_type, elements in element_defs.items():
            if not elements:
                continue
                
            self.logger.debug("要素タイプ %s の処理開始 - %d個", 
                            element_type, len(elements))
            
            for element_def in elements:
                try:
                    # 階層分析実行
                    analysis_result = self.analyze_element_story_relationship(
                        element_def, element_type
                    )
                    
                    story_name = analysis_result.story_name
                    
                    # 階層分析結果を要素定義に追加
                    element_def['assigned_story'] = story_name
                    element_def['analysis_confidence'] = analysis_result.confidence
                    element_def['analysis_method'] = analysis_result.analysis_method
                    
                    # 階層別辞書に追加
                    if story_name not in analyzed_elements:
                        analyzed_elements[story_name] = {}
                    if element_type not in analyzed_elements[story_name]:
                        analyzed_elements[story_name][element_type] = []
                    
                    analyzed_elements[story_name][element_type].append(element_def)
                    processed_elements += 1
                    
                except ConversionError as e:
                    self.logger.warning("要素分析スキップ: %s", str(e))
                    continue
        
        self.logger.info("一括要素分析完了 - 処理済み: %d/%d", 
                        processed_elements, total_elements)
        
        return analyzed_elements
    
    def _analyze_by_floor_attribute(
        self, 
        element_def: Dict[str, Any]
    ) -> Optional[StoryAnalysisResult]:
        """floor属性による判定（最優先）"""
        floor_value = element_def.get('floor')
        
        if floor_value:
            return StoryAnalysisResult(
                story_name=str(floor_value),
                confidence=1.0,
                analysis_method='floor_attribute'
            )
        
        return None
    
    def _analyze_by_node_ids(
        self, 
        element_def: Dict[str, Any], 
        element_type: str
    ) -> Optional[StoryAnalysisResult]:
        """node_idsによる判定（floor属性なしの場合）"""
        representative_nodes = self._get_representative_node_ids(
            element_def, element_type
        )
        
        if not representative_nodes:
            return None
        
        # 代表ノードの階層を取得
        for node_id in representative_nodes:
            if node_id in self.node_story_map:
                story_name = self.node_story_map[node_id]
                return StoryAnalysisResult(
                    story_name=story_name,
                    confidence=0.8,
                    analysis_method='node_ids',
                    node_ids=representative_nodes
                )
        
        return None
    
    def _analyze_by_coordinates(
        self, 
        element_def: Dict[str, Any], 
        element_type: str
    ) -> Optional[StoryAnalysisResult]:
        """座標による判定（最終手段）"""
        if not self.story_elevations:
            return None
        
        # 要素の代表座標を取得
        element_z = self._get_element_z_coordinate(element_def, element_type)
        if element_z is None:
            return None
        
        # 各階層の標高範囲と比較
        for story_name, (base_z, top_z) in self.story_elevations.items():
            if base_z <= element_z <= top_z:
                return StoryAnalysisResult(
                    story_name=story_name,
                    confidence=0.6,
                    analysis_method='coordinates',
                    coordinates=(0.0, 0.0, element_z)  # X,Yは簡略化
                )
        
        return None
    
    def _get_representative_node_ids(
        self, 
        element_def: Dict[str, Any], 
        element_type: str
    ) -> List[str]:
        """要素タイプ別の代表ノードID取得"""
        if element_type not in self.node_selection_strategy:
            return []
        
        node_keys = self.node_selection_strategy[element_type]
        representative_nodes = []
        
        for key in node_keys:
            if '[' in key and ']' in key:
                # 配列アクセス（例: 'node_ids[0]'）
                base_key = key.split('[')[0]
                index = int(key.split('[')[1].split(']')[0])
                
                if base_key in element_def:
                    node_list = element_def[base_key]
                    if isinstance(node_list, list) and len(node_list) > index:
                        representative_nodes.append(node_list[index])
            else:
                # 直接アクセス
                if key in element_def:
                    node_value = element_def[key]
                    if isinstance(node_value, list):
                        representative_nodes.extend(node_value)
                    else:
                        representative_nodes.append(str(node_value))
        
        return [node for node in representative_nodes if node]
    
    def _get_element_z_coordinate(
        self, 
        element_def: Dict[str, Any], 
        element_type: str
    ) -> Optional[float]:
        """要素のZ座標を取得"""
        # 座標情報の取得を試行
        coordinate_keys = [
            'start_point', 'end_point', 'center_point',
            'point', 'coordinates', 'position'
        ]
        
        for key in coordinate_keys:
            if key in element_def:
                coord_data = element_def[key]
                
                if isinstance(coord_data, dict):
                    # 辞書形式の座標
                    z_value = coord_data.get('z', coord_data.get('Z'))
                    if z_value is not None:
                        return float(z_value)
                
                elif isinstance(coord_data, (list, tuple)) and len(coord_data) >= 3:
                    # 配列形式の座標
                    return float(coord_data[2])
        
        return None
    
    def get_analysis_statistics(self) -> Dict[str, int]:
        """分析統計の取得"""
        # 実装は将来の拡張のため保留
        return {
            'total_analyzed': 0,
            'floor_attribute_count': 0,
            'node_ids_count': 0,
            'coordinates_count': 0,
            'failed_count': 0
        }