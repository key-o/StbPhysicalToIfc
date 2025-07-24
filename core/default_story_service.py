"""デフォルトストーリー生成サービス"""

from typing import Dict, List, Set

from utils.logger import get_logger


class DefaultStoryService:
    """デフォルトStory生成を管理するサービス"""
    
    # デフォルト設定
    DEFAULT_STORY_NAME = "GL"
    DEFAULT_STORY_HEIGHT = 3000.0  # 3m
    DEFAULT_STORY_ELEVATION = 0.0
    
    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__)
    
    def create_default_story(
        self,
        beam_defs: List[Dict] = None,
        column_defs: List[Dict] = None,
        brace_defs: List[Dict] = None,
        pile_defs: List[Dict] = None,
        slab_defs: List[Dict] = None,
        wall_defs: List[Dict] = None,
        footing_defs: List[Dict] = None,
        foundation_column_defs: List[Dict] = None,
    ) -> List[Dict]:
        """
        全ての構造要素を含むデフォルトStoryを生成
        
        Args:
            各要素の定義リスト
        
        Returns:
            デフォルトStory定義のリスト（1つの要素）
        """
        # 全ての要素から使用されているnode_idを収集
        all_node_ids = self._collect_all_node_ids(
            beam_defs or [],
            column_defs or [],
            brace_defs or [],
            pile_defs or [],
            slab_defs or [],
            wall_defs or [],
            footing_defs or [],
            foundation_column_defs or [],
        )
        
        default_story = {
            "name": self.DEFAULT_STORY_NAME,
            "height": self.DEFAULT_STORY_HEIGHT,
            "elevation": self.DEFAULT_STORY_ELEVATION,
            "node_ids": sorted(list(all_node_ids)),  # ソートして一貫性を保つ
            "story_type": "DEFAULT",  # デフォルトStoryであることを示すフラグ
        }
        
        self.logger.info(
            f"デフォルトStory '{self.DEFAULT_STORY_NAME}' を生成: "
            f"{len(all_node_ids)}個のノードを含む"
        )
        
        return [default_story]
    
    def _collect_all_node_ids(self, *element_lists: List[Dict]) -> Set[str]:
        """
        全ての要素定義からnode_idを収集
        
        Args:
            element_lists: 各要素タイプの定義リスト
        
        Returns:
            使用されている全てのnode_idのセット
        """
        all_node_ids = set()
        
        for element_list in element_lists:
            if not element_list:
                continue
            
            for element_def in element_list:
                # 各要素タイプに応じてnode_idを収集
                node_ids = self._extract_node_ids_from_element(element_def)
                all_node_ids.update(node_ids)
        
        return all_node_ids
    
    def _extract_node_ids_from_element(self, element_def: Dict) -> List[str]:
        """
        単一要素からnode_idを抽出
        
        Args:
            element_def: 要素定義辞書
        
        Returns:
            要素で使用されているnode_idのリスト
        """
        node_ids = []
        
        # 梁・ブレース
        if "start_node_id" in element_def and "end_node_id" in element_def:
            node_ids.extend([element_def["start_node_id"], element_def["end_node_id"]])
        
        # 柱・杭
        elif "bottom_node_id" in element_def and "top_node_id" in element_def:
            node_ids.extend([element_def["bottom_node_id"], element_def["top_node_id"]])
        
        # フーチング
        elif "node_id" in element_def:
            node_ids.append(element_def["node_id"])
        
        # スラブ・壁（複数ノード）
        elif "node_ids" in element_def:
            if isinstance(element_def["node_ids"], list):
                node_ids.extend(element_def["node_ids"])
            else:
                node_ids.append(element_def["node_ids"])
        
        # primary_node_idがある場合も追加
        elif "primary_node_id" in element_def:
            node_ids.append(element_def["primary_node_id"])
        
        # node_idがない場合のフォールバック
        else:
            self.logger.debug(f"要素からnode_idを抽出できませんでした: {element_def.keys()}")
        
        # 重複を除去してstrに変換
        return [str(nid) for nid in set(node_ids) if nid is not None]
    
    def should_use_default_story(self, story_defs: List[Dict]) -> bool:
        """
        デフォルトStoryを使用すべきかどうかを判定
        
        Args:
            story_defs: 既存のStory定義リスト
        
        Returns:
            True: デフォルトStoryを使用すべき
            False: 既存のStory定義を使用すべき
        """
        if not story_defs:
            self.logger.info("Story定義がないため、デフォルトStoryを使用します")
            return True
        
        if len(story_defs) == 0:
            self.logger.info("Story定義が空のため、デフォルトStoryを使用します")
            return True
        
        # 有効なStory定義が存在する場合
        valid_stories = [
            story for story in story_defs if story.get("name") and story.get("node_ids")
        ]
        
        if not valid_stories:
            self.logger.info("有効なStory定義がないため、デフォルトStoryを使用します")
            return True
        
        self.logger.info(f"既存のStory定義を使用します: {len(valid_stories)}個の階層")
        return False