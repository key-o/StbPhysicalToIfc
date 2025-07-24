"""Element Creation Factory

v2.2.0 統合要素作成ファクトリ
新アーキテクチャベースの統一実装
"""

from typing import Any, Dict, Optional, List
import logging

# v2.2.0: 新統合アーキテクチャのCreatorを使用
from ..creators.beam_creator import BeamCreator
from ..creators.column_creator import ColumnCreator
from ..creators.slab_creator import SlabCreator
from ..creators.wall_creator import WallCreator
from ..creators.brace_creator import BraceCreator

# 特殊要素は必要時にインポート（遅延インポート）

logger = logging.getLogger(__name__)


class ElementCreationFactory:
    """統合要素作成ファクトリ

    v2.2.0: 新アーキテクチャベースの統一実装
    階層化された統合Creatorを使用
    """

    def __init__(self, project_builder=None):
        """初期化

        Args:
            project_builder: IFCプロジェクトビルダー
        """
        self.project_builder = project_builder

        # v2.2.0: 作成要素追跡（StoryConverter要求）
        self.global_created_elements = []

        # 統合Creatorのインスタンス
        self._creators = {
            "beam": BeamCreator(project_builder),
            "column": ColumnCreator(project_builder),
            "slab": SlabCreator(project_builder),
            "wall": WallCreator(project_builder),
            "brace": BraceCreator(project_builder),
        }

        # 使用統計
        self._usage_stats = {
            "beam_created": 0,
            "column_created": 0,
            "slab_created": 0,
            "wall_created": 0,
            "brace_created": 0,
            "pile_created": 0,
            "footing_created": 0,
            "foundation_column_created": 0,
        }

        logger.info("ElementCreationFactory v2.2.0 initialized: Unified Architecture")

    def _resolve_floor_assignment(self, element_def: Dict, default_floor: str) -> str:
        """要素の階層割り当てを解決し、未定義の場合は適切なデフォルトを設定

        Args:
            element_def: 要素定義辞書
            default_floor: デフォルト階層名

        Returns:
            解決された階層名
        """
        floor_name = element_def.get("floor")

        if not floor_name:
            # 階層が未定義の場合はデフォルトを使用
            logger.debug(
                f"要素 {element_def.get('name', 'Unknown')} の階層が未定義のため、デフォルト階層 '{default_floor}' を使用"
            )
            return default_floor

        return floor_name

    def create_beams(self, beam_defs: List[Dict]) -> List:
        """梁要素を生成"""
        try:
            beams = self._creators["beam"].create_elements(beam_defs)

            # 作成要素の追跡
            for i, beam in enumerate(beams):
                if beam:
                    beam_def = beam_defs[i] if i < len(beam_defs) else {}
                    floor_name = self._resolve_floor_assignment(
                        beam_def, "RFL"
                    )  # 梁はデフォルトでRFL階層
                    self.global_created_elements.append(
                        {
                            "type": "beam",
                            "ifc_element": beam,
                            "element": beam,
                            "floor_name": floor_name,
                            "definition": beam_def,
                        }
                    )

            self._usage_stats["beam_created"] += len(beams)
            logger.info(f"v2.2.0: Created {len(beams)} beams via unified BeamCreator")
            return beams

        except Exception as e:
            logger.error(f"v2.2.0: Beam creation failed: {e}")
            return []

    def create_columns(self, column_defs: List[Dict]) -> List:
        """柱要素を生成"""
        try:
            columns = self._creators["column"].create_elements(column_defs)

            # 作成要素の追跡
            for i, column in enumerate(columns):
                if column:
                    column_def = column_defs[i] if i < len(column_defs) else {}
                    floor_name = self._resolve_floor_assignment(
                        column_def, "1FL"
                    )  # 柱はデフォルトで1FL階層
                    self.global_created_elements.append(
                        {
                            "type": "column",
                            "ifc_element": column,
                            "element": column,
                            "floor_name": floor_name,
                            "definition": column_def,
                        }
                    )

            self._usage_stats["column_created"] += len(columns)
            logger.info(
                f"v2.2.0: Created {len(columns)} columns via unified ColumnCreator"
            )
            return columns

        except Exception as e:
            logger.error(f"v2.2.0: Column creation failed: {e}")
            return []

    def create_slabs(self, slab_defs: List[Dict]) -> List:
        """スラブ要素を生成"""
        try:
            slabs = self._creators["slab"].create_elements(slab_defs)

            # 作成要素の追跡
            for i, slab in enumerate(slabs):
                if slab:
                    slab_def = slab_defs[i] if i < len(slab_defs) else {}
                    floor_name = self._resolve_floor_assignment(
                        slab_def, "RFL"
                    )  # スラブはデフォルトでRFL階層
                    self.global_created_elements.append(
                        {
                            "type": "slab",
                            "ifc_element": slab,
                            "element": slab,
                            "floor_name": floor_name,
                            "definition": slab_def,
                        }
                    )

            self._usage_stats["slab_created"] += len(slabs)
            logger.info(f"v2.2.0: Created {len(slabs)} slabs via unified SlabCreator")
            return slabs

        except Exception as e:
            logger.error(f"v2.2.0: Slab creation failed: {e}")
            return []

    def create_walls(self, wall_defs: List[Dict]) -> List:
        """壁要素を生成"""
        try:
            walls = self._creators["wall"].create_elements(wall_defs)

            # 作成要素の追跡
            for i, wall in enumerate(walls):
                if wall:
                    wall_def = wall_defs[i] if i < len(wall_defs) else {}
                    floor_name = self._resolve_floor_assignment(
                        wall_def, "1FL"
                    )  # 壁はデフォルトで1FL階層
                    self.global_created_elements.append(
                        {
                            "type": "wall",
                            "ifc_element": wall,
                            "element": wall,
                            "floor_name": floor_name,
                            "definition": wall_def,
                        }
                    )

            self._usage_stats["wall_created"] += len(walls)
            logger.info(f"v2.2.0: Created {len(walls)} walls via unified WallCreator")
            return walls

        except Exception as e:
            logger.error(f"v2.2.0: Wall creation failed: {e}")
            return []

    def create_braces(self, brace_defs: List[Dict]) -> List:
        """ブレース要素を生成"""
        try:
            braces = self._creators["brace"].create_elements(brace_defs)

            # 作成要素の追跡
            for i, brace in enumerate(braces):
                if brace:
                    brace_def = brace_defs[i] if i < len(brace_defs) else {}
                    floor_name = self._resolve_floor_assignment(
                        brace_def, "1FL"
                    )  # ブレースはデフォルトで1FL階層
                    self.global_created_elements.append(
                        {
                            "type": "brace",
                            "ifc_element": brace,
                            "element": brace,
                            "floor_name": floor_name,
                            "definition": brace_def,
                        }
                    )

            self._usage_stats["brace_created"] += len(braces)
            logger.info(
                f"v2.2.0: Created {len(braces)} braces via unified BraceCreator"
            )
            return braces

        except Exception as e:
            logger.error(f"v2.2.0: Brace creation failed: {e}")
            return []

    def create_creator(self, element_type: str):
        """要素タイプ別Creatorの取得"""
        return self._creators.get(element_type.lower())

    def has_created_elements(self, element_id: str) -> bool:
        """要素IDが作成済みかチェック"""
        return any(
            elem.get("definition", {}).get("id") == element_id
            for elem in self.global_created_elements
        )

    def add_created_element(self, element_info: Dict[str, Any]) -> None:
        """作成済み要素の追加"""
        self.global_created_elements.append(element_info)

    def get_created_elements(self) -> List[Dict]:
        """作成済み要素リストの取得"""
        return self.global_created_elements.copy()

    def get_usage_stats(self) -> Dict[str, int]:
        """使用統計の取得"""
        return self._usage_stats.copy()

    def reset_stats(self):
        """統計のリセット"""
        for key in self._usage_stats:
            self._usage_stats[key] = 0
        self.global_created_elements.clear()
        for creator in self._creators.values():
            creator.reset_count()
        logger.info("v2.2.0: Usage statistics and created elements reset")

    def filter_uncreated_elements(self, element_defs: List[Dict]) -> List[Dict]:
        """作成されていない要素をフィルタリング"""
        created_ids = {
            elem.get("definition", {}).get("id")
            for elem in self.global_created_elements
        }
        return [
            elem_def
            for elem_def in element_defs
            if elem_def.get("id") not in created_ids
        ]

    def is_element_created_by_name(
        self, element_name: str, element_type: str = None
    ) -> bool:
        """要素名で作成済みかチェック"""
        for elem in self.global_created_elements:
            elem_def = elem.get("definition", {})
            if elem_def.get("name") == element_name:
                if element_type is None or elem.get("type") == element_type:
                    return True
        return False

    # 特殊要素（遅延インポートで実装）
    def create_piles(self, pile_defs: List[Dict]) -> List:
        """杭要素を生成"""
        try:
            # 遅延インポート
            from ..specialized.pile_creator import IFCPileCreator

            creator = IFCPileCreator(self.project_builder)
            piles = (
                creator.create_piles(pile_defs)
                if hasattr(creator, "create_piles")
                else []
            )

            for i, pile in enumerate(piles):
                if pile:
                    pile_def = pile_defs[i] if i < len(pile_defs) else {}
                    floor_name = self._resolve_floor_assignment(
                        pile_def, "GL"
                    )  # 杭はデフォルトでGL階層
                    self.global_created_elements.append(
                        {
                            "type": "pile",
                            "ifc_element": pile,
                            "element": pile,
                            "floor_name": floor_name,
                            "definition": pile_def,
                        }
                    )

            self._usage_stats["pile_created"] += len(piles)
            logger.info(f"v2.2.0: Created {len(piles)} piles")
            return piles

        except Exception as e:
            logger.error(f"v2.2.0: Pile creation failed: {e}")
            return []

    def create_footings(self, footing_defs: List[Dict]) -> List:
        """フーチング要素を生成"""
        try:
            # 遅延インポート
            from ..specialized.footing_creator import IFCFootingCreator

            creator = IFCFootingCreator(self.project_builder)
            footings = (
                creator.create_footings(footing_defs)
                if hasattr(creator, "create_footings")
                else []
            )

            for i, footing in enumerate(footings):
                if footing:
                    footing_def = footing_defs[i] if i < len(footing_defs) else {}
                    floor_name = self._resolve_floor_assignment(
                        footing_def, "GL"
                    )  # フーチングはデフォルトでGL階層
                    self.global_created_elements.append(
                        {
                            "type": "footing",
                            "ifc_element": footing,
                            "element": footing,
                            "floor_name": floor_name,
                            "definition": footing_def,
                        }
                    )

            self._usage_stats["footing_created"] += len(footings)
            logger.info(f"v2.2.0: Created {len(footings)} footings")
            return footings

        except Exception as e:
            logger.error(f"v2.2.0: Footing creation failed: {e}")
            return []

    def create_foundation_columns(self, foundation_column_defs: List[Dict]) -> List:
        """基礎柱要素を生成"""
        try:
            # 遅延インポート
            from ..specialized.foundation_column_creator import (
                IFCFoundationColumnCreator,
            )

            creator = IFCFoundationColumnCreator(self.project_builder)
            foundation_columns = (
                creator.create_foundation_columns(foundation_column_defs)
                if hasattr(creator, "create_foundation_columns")
                else []
            )

            for i, foundation_column in enumerate(foundation_columns):
                if foundation_column:
                    foundation_column_def = (
                        foundation_column_defs[i]
                        if i < len(foundation_column_defs)
                        else {}
                    )
                    floor_name = self._resolve_floor_assignment(
                        foundation_column_def, "GL"
                    )  # 基礎柱はデフォルトでGL階層
                    self.global_created_elements.append(
                        {
                            "type": "foundation_column",
                            "ifc_element": foundation_column,
                            "element": foundation_column,
                            "floor_name": floor_name,
                            "definition": foundation_column_def,
                        }
                    )

            self._usage_stats["foundation_column_created"] += len(foundation_columns)
            logger.info(f"v2.2.0: Created {len(foundation_columns)} foundation columns")
            return foundation_columns

        except Exception as e:
            logger.error(f"v2.2.0: Foundation column creation failed: {e}")
            return []
