"""
StoryElementRelationshipManager - 階層-要素間の空間関係管理クラス
要素と階層の空間関係を効率的に管理し、IFC標準に準拠した関連付けを行う
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from utils.logger import get_logger
from exceptions.custom_errors import ConversionError
from .element_centric_converter import ElementInfo


@dataclass
class StoryStatistics:
    """階層統計情報"""
    story_name: str
    element_count: int = 0
    element_types: Dict[str, int] = field(default_factory=dict)
    total_volume: float = 0.0
    confidence_average: float = 0.0


@dataclass
class ValidationResult:
    """関係整合性検証結果"""
    is_valid: bool
    orphaned_elements: List[ElementInfo] = field(default_factory=list)
    duplicate_relationships: List[str] = field(default_factory=list)
    missing_stories: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StoryElementRelationshipManager:
    """
    階層-要素間の空間関係管理クラス
    
    特徴:
    - IFC標準準拠の空間関係作成
    - 効率的な一括処理
    - 関係整合性検証
    - 統計情報とパフォーマンス監視
    """
    
    def __init__(self, project_builder, logger=None):
        """
        Args:
            project_builder: IFCProjectBuilder インスタンス
            logger: ログ出力用ロガー
        """
        self.project_builder = project_builder
        self.logger = logger or get_logger(__name__)
        
        # 階層-要素マッピング
        self.story_elements_map: Dict[str, List[ElementInfo]] = {}
        
        # IFC空間関係オブジェクト
        self.spatial_relationships: List[Any] = []
        
        # 検証用セット
        self.registered_element_ids: Set[str] = set()
        self.created_story_names: Set[str] = set()
        
        self.logger.info("StoryElementRelationshipManager初期化完了")
    
    def register_element_to_story(
        self, 
        element_info: ElementInfo, 
        story_name: str
    ) -> None:
        """
        要素を階層に登録
        
        Args:
            element_info: 要素情報
            story_name: 階層名
        """
        # 重複登録チェック
        if element_info.element_id in self.registered_element_ids:
            self.logger.warning("要素重複登録: %s", element_info.element_id)
            return
        
        # 階層別リストに追加
        if story_name not in self.story_elements_map:
            self.story_elements_map[story_name] = []
        
        self.story_elements_map[story_name].append(element_info)
        self.registered_element_ids.add(element_info.element_id)
        
        self.logger.debug("要素登録: %s -> %s", element_info.element_id, story_name)
    
    def create_spatial_relationships(self) -> List[Any]:
        """
        空間関係(IfcRelContainedInSpatialStructure)を一括作成
        
        Returns:
            List[Any]: 作成されたIFC空間関係オブジェクトのリスト
        """
        self.logger.info("空間関係作成開始 - 階層数: %d", 
                        len(self.story_elements_map))
        
        spatial_relationships = []
        
        try:
            # 階層ごとに空間関係を作成
            for story_name, element_infos in self.story_elements_map.items():
                if not element_infos:
                    continue
                
                # 階層オブジェクトを取得
                storey = self._get_storey_by_name(story_name)
                if not storey:
                    self.logger.warning("階層が見つかりません: %s", story_name)
                    continue
                
                # IFC要素リストを作成
                ifc_elements = [info.ifc_element for info in element_infos 
                              if info.ifc_element is not None]
                
                if not ifc_elements:
                    self.logger.warning("階層%sにIFC要素が存在しません", story_name)
                    continue
                
                # IfcRelContainedInSpatialStructure を作成
                rel_contained = self._create_spatial_relationship(storey, ifc_elements)
                if rel_contained:
                    spatial_relationships.append(rel_contained)
                    self.logger.debug("空間関係作成: %s (%d要素)", 
                                    story_name, len(ifc_elements))
            
            self.spatial_relationships = spatial_relationships
            self.logger.info("空間関係作成完了 - 関係数: %d", len(spatial_relationships))
            
            return spatial_relationships
            
        except Exception as e:
            error_msg = f"空間関係作成エラー: {str(e)}"
            self.logger.error(error_msg)
            raise ConversionError(error_msg) from e
    
    def associate_elements_to_storeys(
        self, 
        created_storeys: Dict[str, Any]
    ) -> None:
        """
        作成済み階層に要素を関連付け
        
        Args:
            created_storeys: {story_name: IfcBuildingStorey} の辞書
        """
        self.logger.info("階層関連付け開始 - 階層数: %d", len(created_storeys))
        
        # 利用可能な階層名を記録
        self.created_story_names.update(created_storeys.keys())
        
        # 既存の登録済み要素を階層に関連付け
        total_associated = 0
        
        for story_name, element_infos in self.story_elements_map.items():
            if story_name in created_storeys:
                storey = created_storeys[story_name]
                
                # 要素を階層に関連付け
                for element_info in element_infos:
                    try:
                        self._associate_element_to_storey(element_info, storey)
                        total_associated += 1
                    except Exception as e:
                        self.logger.warning("要素関連付け失敗 %s: %s", 
                                          element_info.element_id, str(e))
            else:
                self.logger.warning("階層が見つかりません: %s", story_name)
        
        self.logger.info("階層関連付け完了 - 関連付け数: %d", total_associated)
    
    def validate_relationships(self) -> ValidationResult:
        """
        関係の整合性検証
        
        Returns:
            ValidationResult: 検証結果
        """
        self.logger.info("関係整合性検証開始")
        
        orphaned_elements = []
        duplicate_relationships = []
        missing_stories = []
        warnings = []
        
        # 1. 孤立要素チェック
        for story_name, element_infos in self.story_elements_map.items():
            if story_name not in self.created_story_names:
                missing_stories.append(story_name)
                orphaned_elements.extend(element_infos)
        
        # 2. 重複関係チェック
        element_id_counts = {}
        for element_infos in self.story_elements_map.values():
            for element_info in element_infos:
                element_id = element_info.element_id
                element_id_counts[element_id] = element_id_counts.get(element_id, 0) + 1
        
        duplicate_relationships = [
            element_id for element_id, count in element_id_counts.items() 
            if count > 1
        ]
        
        # 3. 統計警告
        total_elements = sum(len(infos) for infos in self.story_elements_map.values())
        if total_elements == 0:
            warnings.append("登録要素が存在しません")
        
        low_confidence_count = sum(
            1 for infos in self.story_elements_map.values() 
            for info in infos if info.confidence < 0.7
        )
        
        if low_confidence_count > 0:
            warnings.append(f"低信頼度要素: {low_confidence_count}個")
        
        is_valid = (
            len(orphaned_elements) == 0 and 
            len(duplicate_relationships) == 0 and 
            len(missing_stories) == 0
        )
        
        result = ValidationResult(
            is_valid=is_valid,
            orphaned_elements=orphaned_elements,
            duplicate_relationships=duplicate_relationships,
            missing_stories=missing_stories,
            warnings=warnings
        )
        
        self.logger.info("関係整合性検証完了 - 有効: %s", is_valid)
        
        if not is_valid:
            self.logger.warning("検証問題: 孤立要素%d, 重複関係%d, 欠落階層%d",
                               len(orphaned_elements), 
                               len(duplicate_relationships),
                               len(missing_stories))
        
        return result
    
    def get_elements_by_story(self, story_name: str) -> List[ElementInfo]:
        """
        指定階層の要素取得
        
        Args:
            story_name: 階層名
            
        Returns:
            List[ElementInfo]: 階層内の要素リスト
        """
        return self.story_elements_map.get(story_name, [])
    
    def get_story_statistics(self) -> Dict[str, StoryStatistics]:
        """
        階層別統計情報取得
        
        Returns:
            Dict[str, StoryStatistics]: 階層名をキーとした統計情報
        """
        statistics = {}
        
        for story_name, element_infos in self.story_elements_map.items():
            if not element_infos:
                continue
            
            # 要素タイプ別カウント
            element_types = {}
            confidence_sum = 0.0
            
            for element_info in element_infos:
                element_type = element_info.element_type
                element_types[element_type] = element_types.get(element_type, 0) + 1
                confidence_sum += element_info.confidence
            
            # 統計作成
            stats = StoryStatistics(
                story_name=story_name,
                element_count=len(element_infos),
                element_types=element_types,
                confidence_average=confidence_sum / len(element_infos) if element_infos else 0.0
            )
            
            statistics[story_name] = stats
        
        return statistics
    
    def _get_storey_by_name(self, story_name: str) -> Optional[Any]:
        """階層名から階層オブジェクトを取得"""
        try:
            # project_builderから階層を取得
            # 実装はproject_builderの仕様に依存
            return self.project_builder.get_storey_by_name(story_name)
        except Exception as e:
            self.logger.warning("階層取得失敗 %s: %s", story_name, str(e))
            return None
    
    def _create_spatial_relationship(
        self, 
        storey: Any, 
        ifc_elements: List[Any]
    ) -> Optional[Any]:
        """IFC空間関係を作成"""
        try:
            # IFC標準に準拠したIfcRelContainedInSpatialStructure作成
            # 実装はproject_builderのIFCライブラリに依存
            return self.project_builder.create_spatial_relationship(storey, ifc_elements)
        except Exception as e:
            self.logger.warning("空間関係作成失敗: %s", str(e))
            return None
    
    def _associate_element_to_storey(
        self, 
        element_info: ElementInfo, 
        storey: Any
    ) -> None:
        """要素を階層に関連付け"""
        try:
            # プロジェクトビルダーの関連付け機能を使用
            # 実装はproject_builderの仕様に依存
            if hasattr(self.project_builder, 'associate_element_to_storey'):
                self.project_builder.associate_element_to_storey(
                    element_info.ifc_element, storey
                )
        except Exception as e:
            self.logger.debug("要素関連付け警告 %s: %s", element_info.element_id, str(e))
    
    def get_total_registered_elements(self) -> int:
        """登録要素の総数を取得"""
        return sum(len(infos) for infos in self.story_elements_map.values())
    
    def get_story_names(self) -> List[str]:
        """登録されている階層名のリストを取得"""
        return list(self.story_elements_map.keys())
    
    def clear_all_relationships(self) -> None:
        """すべての関係をクリア"""
        self.story_elements_map.clear()
        self.spatial_relationships.clear()
        self.registered_element_ids.clear()
        self.created_story_names.clear()
        
        self.logger.info("すべての関係をクリアしました")