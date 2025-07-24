"""StbStory から IfcBuildingStorey への変換クラス - リファクタリング版"""

from typing import Dict, List, Optional
import ifcopenshell
from .ifc_project_builder import IFCProjectBuilder

# ElementTrackerはElementCreationFactoryに統合済み
# ElementFilterServiceとSpatialRelationshipManagerも統合済み
from .element_creation_factory import ElementCreationFactory

from utils.logger import get_logger
import logging

logger = get_logger(__name__)


class StbToIfcStoryConverter:
    """StbStory 定義を IfcBuildingStorey に変換する - 統合版

    以下の機能を統合：
    - ElementCreationFactory: 要素生成・追跡管理（ElementTracker統合済み）
    - ElementFilterService: 要素フィルタリング（統合済み）
    - SpatialRelationshipManager: 空間関係管理（統合済み）
    """

    def __init__(self, project_builder: "IFCProjectBuilder", xml_content=None):
        """コンバータを初期化

        Args:
            project_builder: IFCプロジェクト構築用ビルダー
            xml_content: STBファイルのXMLコンテンツ
        """
        self.project_builder = project_builder
        self.file = project_builder.file
        self.owner_history = project_builder.owner_history
        self.xml_content = xml_content
        self.element_definitions = None
        self.current_story_name = None

        # 生成済み階層を保存
        self.created_storeys: Dict[str, "ifcopenshell.entity_instance"] = (
            {}
        )  # 各種サービスを初期化（統合済み機能のみ）
        self.element_creator = ElementCreationFactory(project_builder)

        # ElementFilterService機能を統合
        self.node_story_map = {}

        # SpatialRelationshipManager機能を統合（プロジェクトビルダーと履歴を保持）

    def set_element_definitions(self, element_defs: Dict):
        """事前に変換された要素定義を設定

        Args:
            element_defs: 各要素タイプの定義辞書
        """
        self.element_definitions = element_defs

    def set_node_story_map(self, mapping: Dict[str, str]) -> None:
        """節点IDと階名の対応辞書を設定（ElementFilterService統合）

        Args:
            mapping: 節点IDと階名の対応辞書
        """
        self.node_story_map = mapping

    def convert_stb_story_to_ifc_story(
        self, story_def: Dict
    ) -> "ifcopenshell.entity_instance":
        """StbStory 定義から IfcBuildingStorey を生成

        Args:
            story_def: 解析済みの StbStory 情報

        Returns:
            生成された IfcBuildingStorey
        """
        name = story_def.get("name", "Storey")
        height = float(story_def.get("height", 0.0))
        elevation = height / 1000.0  # mm から m へ変換

        logger.info("StbStory '%s' を高さ %.3fm で変換", name, elevation)

        storey, placement = self.project_builder.add_storey(name, elevation)

        # 階層を登録
        self.created_storeys[name] = storey  # 現在の階層をプロジェクトビルダーに反映
        self.project_builder.storey = storey
        self.project_builder.storey_placement = placement

        return storey

    def ensure_gl_storey_exists(self) -> None:
        """関連するフロアが見つからない要素用のGL階層を事前作成

        GL階層が存在しない場合は新規作成し、ログに記録します。
        """
        if "GL" not in self.created_storeys:
            logger.info(
                "関連するフロアが見つからない要素用のGL階層を事前作成します（高さ0.0m）"
            )
            gl_storey, gl_placement = self.project_builder.add_storey("GL", 0.0)
            self.created_storeys["GL"] = gl_storey
            self.project_builder.storey = gl_storey
            self.project_builder.storey_placement = gl_placement

    def convert_elements_for_story(self, story_def: Dict) -> None:
        """指定したStoryに紐づく全Stb要素をIfc要素に変換

        Args:
            story_def: 階層定義辞書
        """
        # 現在処理中の階層名を保存
        self.current_story_name = story_def.get("name")
        logger.info("要素関連付け開始: Story '%s'", self.current_story_name)

        # 要素定義を取得
        element_defs = self._get_element_definitions()

        if not element_defs:
            logger.warning("要素定義が取得できませんでした。要素変換をスキップします。")
            return

        # 各要素定義に対して階情報を設定
        # node_story_map を参照して要素の階を定義に追加
        for elem_type, defs in element_defs.items():
            for d in defs:
                # 線要素 (梁・柱等) は bottom_node_id/top_node_id から階取得
                # 壁要素は primary_node_id を使用
                nid = None
                if d.get("bottom_node_id"):
                    nid = str(d["bottom_node_id"])
                elif d.get("start_node_id"):
                    nid = str(d["start_node_id"])
                elif d.get("node_id"):
                    nid = str(d["node_id"])
                elif d.get("primary_node_id"):
                    nid = str(d["primary_node_id"])
                # 階名を設定
                if nid and self.node_story_map.get(nid):
                    d["floor"] = self.node_story_map[nid]
                else:
                    # デフォルト階を設定
                    d["floor"] = self.current_story_name

        # フィルタリング処理を行う（現状バイパス）
        filtered_defs = element_defs

        # 未作成要素のみを抽出（グローバル重複チェック）
        # 重複チェックを有効化（重複要素作成問題の修正）
        uncreated_defs = self._filter_uncreated_elements(filtered_defs)

        # さらに要素名による重複チェックを実行
        # 名前・位置重複チェックを有効化（重複要素作成問題の修正）
        deduplicated_defs = self._deduplicate_by_name_and_position(uncreated_defs)

        # 要素を生成
        self._create_elements(deduplicated_defs)

        logger.info("要素変換完了: Story '%s'", self.current_story_name)

    def associate_elements_to_storeys(self) -> None:
        """全ての作成済み要素を適切な階層に関連付ける（重複なし）（SpatialRelationshipManager統合）"""
        created_storeys = self.created_storeys
        global_created_elements = self.element_creator.global_created_elements

        if not global_created_elements:
            logger.warning("作成済み要素が存在しないため、関連付けをスキップします")
            return

        # 関連するフロアが見つからない要素用のGL階層を事前作成
        self.ensure_gl_storey_exists()

        if not created_storeys:
            logger.warning("階層が作成されていないため、関連付けをスキップします")
            return

        # ストーリー名ごとに要素リストを初期化
        storey_elements = {name: [] for name in created_storeys.keys()}

        # 登録時の階層名で素早く要素をグループ化
        for element_info in global_created_elements:
            ifc_element = element_info.get("ifc_element")
            floor_name = element_info.get("floor_name")

            if not ifc_element or not floor_name:
                continue

            if floor_name in storey_elements:
                storey_elements[floor_name].append(ifc_element)
            else:
                # 関連するフロアが見つからない要素は、GLという階を作成してそこに紐づける
                logger.info(
                    "要素 %s の登録階層 '%s' が未定義のため、GL階層に紐づけます",
                    ifc_element.GlobalId,
                    floor_name,
                )

                # GLストーリーが存在しない場合は新規作成
                if "GL" not in created_storeys:
                    logger.info(
                        "関連するフロアが見つからない要素用のGL階層を新規作成します（高さ0.0m）"
                    )
                    gl_storey, gl_placement = self.project_builder.add_storey("GL", 0.0)
                    created_storeys["GL"] = gl_storey
                    storey_elements["GL"] = []
                    self.created_storeys["GL"] = gl_storey

                # 要素をGL階層に追加
                storey_elements["GL"].append(ifc_element)

        # 空間関係を生成
        for storey_name, elements in storey_elements.items():
            if not elements:
                continue

            storey = created_storeys.get(storey_name)
            if not storey:
                continue

            try:
                rel = self.file.createIfcRelContainedInSpatialStructure(
                    GlobalId=ifcopenshell.guid.new(),
                    OwnerHistory=self.owner_history,
                    RelatedElements=elements,
                    RelatingStructure=storey,
                )
                logger.info(
                    "階層 '%s' に %d個の要素を関連付けました: %s",
                    storey_name,
                    len(elements),
                    rel.GlobalId,
                )

                # GL階層に紐づけられた要素の詳細をログ出力
                if storey_name == "GL":
                    element_types = {}
                    for element in elements:
                        element_type = element.is_a()
                        element_types[element_type] = (
                            element_types.get(element_type, 0) + 1
                        )

                    logger.info(
                        "GL階層に紐づけられた要素の内訳: %s",
                        ", ".join(
                            [
                                f"{etype}: {count}個"
                                for etype, count in element_types.items()
                            ]
                        ),
                    )
            except Exception as e:
                logger.error("階層 '%s' への要素関連付け中にエラー: %s", storey_name, e)

    def filter_elements_by_story(
        self, elements: List[Dict], story_def: Dict
    ) -> List[Dict]:
        """要素を指定階層に基づいてフィルタリングする（ElementFilterService統合）

        Args:
            elements: フィルタリング対象の要素リスト
            story_def: 階層定義

        Returns:
            フィルタリングされた要素リスト
        """
        filtered_elements: List[Dict] = []
        floor_name = story_def.get("name")
        story_node_ids = story_def.get("node_ids", [])

        logger.debug(
            "フィルタリング対象: %d個の要素を階層'%s'で判定",
            len(elements),
            floor_name,
        )

        for i, element in enumerate(elements):
            element_id = element.get("id", f"unknown_{i}")
            element_floor = element.get("floor")
            element_type = element.get("type", "").lower()

            # ブレースの場合は詳細ログを出力
            if "brace" in str(element.get("id", "")).lower() or "ブレース" in str(
                element.get("name", "")
            ):
                logger.debug(
                    "ブレース%s フィルタリング詳細: floor='%s', start_node_id='%s', end_node_id='%s'",
                    element_id,
                    element_floor,
                    element.get("start_node_id"),
                    element.get("end_node_id"),
                )

            # 要素が含まれるかの判定フラグ
            should_include = False

            # 1. floor属性による判定（最優先）
            if element_floor == floor_name:
                should_include = True
                logger.debug(
                    "要素 %s を floor属性 '%s' により階層 '%s' に関連付け",
                    element_id,
                    element_floor,
                    floor_name,
                )
            # floor属性が明確に設定されている場合は、他の判定をスキップ
            elif element_floor and element_floor != floor_name:
                # 明確に別の階層に属するので除外
                logger.debug(
                    "要素 %s は floor属性 '%s' により階層 '%s' から除外",
                    element_id,
                    element_floor,
                    floor_name,
                )
            # 2. floor属性がない場合のみ、node_idsによる判定
            elif (
                not element_floor
                and story_node_ids
                and self._element_belongs_to_story_by_nodes(
                    element, story_node_ids, floor_name
                )
            ):
                should_include = True
                logger.debug(
                    "要素 %s を node_ids により階層 '%s' に関連付け",
                    element_id,
                    floor_name,
                )
            # 3. floor属性がない場合のみ、座標による判定
            elif not element_floor and self._element_belongs_to_story_by_coordinates(
                element, story_def
            ):
                should_include = True
                logger.debug(
                    "要素 %s を座標により階層 '%s' に関連付け",
                    element_id,
                    floor_name,
                )
            # 4. 寛容な判定: 壁・スラブでfloor属性がない場合は含める
            elif element_type in ["wall", "slab"] and not element_floor:
                should_include = True
                logger.debug(
                    "要素 %s (type=%s) をfloor属性なしのため階層 '%s' に関連付け",
                    element_id,
                    element_type,
                    floor_name,
                )

            if should_include:
                filtered_elements.append(element)
            else:
                # フィルタリングで除外された要素をログ出力
                if "brace" in str(element.get("id", "")).lower() or "ブレース" in str(
                    element.get("name", "")
                ):
                    logger.warning(
                        "ブレース%s が階層'%s'から除外されました: floor='%s', node判定=False, 座標判定=False",
                        element_id,
                        floor_name,
                        element_floor,
                    )

        logger.debug(
            "フィルタリング結果: %d個の要素が階層'%s'に関連付けられました",
            len(filtered_elements),
            floor_name,
        )

        return filtered_elements

    def _get_element_definitions(self) -> Dict:
        """要素定義を取得

        Returns:
            要素定義の辞書
        """
        if self.element_definitions:
            return (
                self.element_definitions
            )  # XMLコンテンツから要素定義を解析        if not self.xml_content:
            logger.warning("XMLコンテンツが提供されていません")
            return {}

        try:
            from stbParser.unified_stb_parser import UnifiedSTBParser, ElementType

            parser = UnifiedSTBParser(self.xml_content)
            element_defs = {
                "beam_defs": parser.parse_element_type(ElementType.BEAM),
                "column_defs": parser.parse_element_type(ElementType.COLUMN),
                "brace_defs": parser.parse_element_type(ElementType.BRACE),
                "pile_defs": parser.parse_element_type(ElementType.PILE),
                "slab_defs": parser.parse_element_type(ElementType.SLAB),
                "wall_defs": parser.parse_element_type(ElementType.WALL),
                "footing_defs": parser.parse_element_type(ElementType.FOOTING),
                "foundation_column_defs": parser.parse_element_type(
                    ElementType.FOUNDATION_COLUMN
                ),
            }

            logger.info(
                "XMLから要素定義を解析: 梁=%d, 柱=%d, ブレース=%d, 杭=%d, スラブ=%d, 壁=%d, フーチング=%d, 基礎柱=%d",
                len(element_defs["beam_defs"]),
                len(element_defs["column_defs"]),
                len(element_defs["brace_defs"]),
                len(element_defs["pile_defs"]),
                len(element_defs["slab_defs"]),
                len(element_defs["wall_defs"]),
                len(element_defs["footing_defs"]),
                len(element_defs["foundation_column_defs"]),
            )

            return element_defs

        except Exception as e:
            logger.error("要素定義の解析中にエラーが発生しました: %s", e)
            return {}

    # === ElementFilterService統合メソッド ===

    def _element_belongs_to_story_by_nodes(
        self, element: Dict, story_node_ids: List[str], floor_name: str | None = None
    ) -> bool:
        """node_idsによる要素の階層判定
        要素タイプ別に特定のノードのみで判定し、重複配置を防ぐ

        Args:
            element: 要素定義辞書
            story_node_ids: 階層に属するノードIDリスト
            floor_name: 階層名

        Returns:
            要素が階層に属する場合True
        """
        element_type = element.get("type", "").lower()

        # 要素タイプ別に特定のノードのみを使用して判定
        if element_type in ["beam", "girder", "brace"]:
            # 梁・ガーダー・ブレース: 始点ノードのみで判定
            start_node_id = element.get("start_node_id")
            if start_node_id:
                if self.node_story_map and floor_name:
                    return self.node_story_map.get(start_node_id) == floor_name
                else:
                    return start_node_id in story_node_ids
            return False

        elif element_type in ["column", "pile", "foundationcolumn"]:
            # 柱・杭・基礎柱: 下端ノードのみで判定
            bottom_node_id = element.get("bottom_node_id")
            if bottom_node_id:
                if self.node_story_map and floor_name:
                    return self.node_story_map.get(bottom_node_id) == floor_name
                else:
                    return bottom_node_id in story_node_ids
            return False

        elif element_type in ["wall", "slab"]:
            # 壁・スラブ: NodeIdListの最初のノードのみで判定
            node_ids = element.get("node_ids", [])
            if node_ids:
                first_node_id = node_ids[0]
                if self.node_story_map and floor_name:
                    return self.node_story_map.get(first_node_id) == floor_name
                else:
                    return first_node_id in story_node_ids

            # primary_node_idがある場合はそれを使用
            primary_node_id = element.get("primary_node_id")
            if primary_node_id:
                if self.node_story_map and floor_name:
                    return self.node_story_map.get(primary_node_id) == floor_name
                else:
                    return primary_node_id in story_node_ids
            return False

        else:
            # その他の要素: 単一ノードIDで判定
            node_id = element.get("node_id")
            if node_id:
                if self.node_story_map and floor_name:
                    return self.node_story_map.get(node_id) == floor_name
                else:
                    return node_id in story_node_ids
            return False

    def _element_belongs_to_story_by_coordinates(
        self, element: Dict, story_def: Dict
    ) -> bool:
        """座標による階層判定

        Args:
            element: 要素定義辞書
            story_def: 階層定義

        Returns:
            要素が階層に属する場合True
        """
        z = self._get_element_z_coordinate(element)
        if z is None:
            return False

        base_z = float(story_def.get("height", 0.0))
        top_z = base_z + float(story_def.get("floor_height", 3000.0))
        return base_z <= z < top_z

    def _get_element_z_coordinate(self, element: Dict) -> Optional[float]:
        """要素から代表Z座標を取得

        Args:
            element: 要素定義辞書

        Returns:
            代表Z座標（取得できない場合None）
        """
        # 梁・ブレース：開始点と終了点の中点
        if "start_point" in element and "end_point" in element:
            sp = element["start_point"]
            ep = element["end_point"]
            if all(p is not None for p in (sp, ep)):
                return (float(sp["z"]) + float(ep["z"])) / 2.0

        # 柱・杭：下端点と上端点の中点
        if "bottom_point" in element and "top_point" in element:
            bp = element["bottom_point"]
            tp = element["top_point"]
            if all(p is not None for p in (bp, tp)):
                return (float(bp["z"]) + float(tp["z"])) / 2.0

        # 単一点要素
        if "point" in element:
            return float(element["point"]["z"])

        # 上端点のみ
        if "top_point" in element:
            return float(element["top_point"]["z"])

        # 下端点のみ
        if "bottom_point" in element:
            return float(element["bottom_point"]["z"])

        return None

    def _filter_elements_by_story(self, element_defs: Dict, story_def: Dict) -> Dict:
        """要素を階層でフィルタリング

        Args:
            element_defs: 要素定義辞書
            story_def: 階層定義

        Returns:
            フィルタリングされた要素定義辞書
        """
        filtered_defs = {}

        for element_type, elements in element_defs.items():
            if elements:
                filtered_elements = self.filter_elements_by_story(elements, story_def)
                filtered_defs[element_type] = filtered_elements

                logger.debug(
                    "階層'%s'の%s: %d個をフィルタリング",
                    story_def.get("name"),
                    element_type,
                    len(filtered_elements),
                )
            else:
                filtered_defs[element_type] = []

        return filtered_defs

    def _filter_uncreated_elements(self, element_defs: Dict) -> Dict:
        """未作成要素のみを抽出

        Args:
            element_defs: 要素定義辞書

        Returns:
            未作成要素のみの辞書
        """
        uncreated_defs = {}

        for element_type, elements in element_defs.items():
            if elements:
                uncreated_elements = self.element_creator.filter_uncreated_elements(
                    elements
                )
                uncreated_defs[element_type] = uncreated_elements

                logger.debug(
                    "%s: %d個の未作成要素を抽出",
                    element_type,
                    len(uncreated_elements),
                )
            else:
                uncreated_defs[element_type] = []

        return uncreated_defs

    def _deduplicate_by_name_and_position(self, element_defs: Dict) -> Dict:
        """要素名と位置による厳密な重複チェック

        Args:
            element_defs: 要素定義辞書

        Returns:
            重複除去後の要素定義辞書
        """
        deduplicated_defs = {}

        for element_type, elements in element_defs.items():
            if not elements:
                deduplicated_defs[element_type] = []
                continue

            unique_elements = []
            for element in elements:
                element_name = element.get("name") or element.get(
                    "stb_section_name", ""
                )

                # ElementCreationFactoryの名前チェックを使用
                if element_name and self.element_creator.is_element_created_by_name(
                    element_name
                ):
                    logger.debug(
                        "要素名 '%s' は他の階層で既に作成済みのためスキップ (階層: %s)",
                        element_name,
                        self.current_story_name,
                    )
                    continue
                else:
                    unique_elements.append(element)

            deduplicated_defs[element_type] = unique_elements

            if unique_elements:
                logger.debug(
                    "階層'%s'の%s: %d個の一意要素を抽出",
                    self.current_story_name,
                    element_type,
                    len(unique_elements),
                )

        return deduplicated_defs

    def _create_elements(self, element_defs: Dict) -> None:
        """要素を生成

        Args:
            element_defs: 要素定義辞書
        """
        total_created = 0

        # 梁の生成
        if element_defs.get("beam_defs"):
            beams = self.element_creator.create_beams(element_defs["beam_defs"])
            total_created += len(beams)

        # 柱の生成
        if element_defs.get("column_defs"):
            columns = self.element_creator.create_columns(element_defs["column_defs"])
            total_created += len(columns)

        # ブレースの生成
        if element_defs.get("brace_defs"):
            braces = self.element_creator.create_braces(element_defs["brace_defs"])
            total_created += len(braces)

        # 杭の生成
        if element_defs.get("pile_defs"):
            piles = self.element_creator.create_piles(element_defs["pile_defs"])
            total_created += len(piles)

        # スラブの生成
        if element_defs.get("slab_defs"):
            slabs = self.element_creator.create_slabs(element_defs["slab_defs"])
            total_created += len(slabs)  # 壁の生成
        # 壁の生成
        if element_defs.get("wall_defs"):
            logger.info(f"壁定義が見つかりました: {len(element_defs['wall_defs'])}個")
            walls = self.element_creator.create_walls(element_defs["wall_defs"])
            total_created += len(walls)
        else:
            # 壁要素は通常、複数階層にまたがるため、最初の階層でのみ作成される
            # 他の階層では既に作成済みとして扱われるため、DEBUGレベルでログ出力
            logger.debug(f"階層 '{self.current_story_name}' に未作成の壁要素がありません (既に作成済みまたは該当なし)")
            logger.debug(
                f"element_defsのキー: {list(element_defs.keys())}"
            )
            # 要素数の詳細をDEBUGレベルで記録
            for key, value in element_defs.items():
                if isinstance(value, list):
                    logger.debug(f"  {key}: {len(value)}個")
                else:
                    logger.debug(f"  {key}: {type(value)}")  # フーチングの生成
        if element_defs.get("footing_defs"):
            footings = self.element_creator.create_footings(
                element_defs["footing_defs"]
            )
            total_created += len(footings)

        # 基礎柱の生成
        if element_defs.get("foundation_column_defs"):
            foundation_columns = self.element_creator.create_foundation_columns(
                element_defs["foundation_column_defs"]
            )
            total_created += len(foundation_columns)

        logger.info(
            "階層'%s'で合計%d個の要素を生成しました",
            self.current_story_name,
            total_created,
        )
