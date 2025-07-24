"""IFC生成サービス - IFC生成の責務のみを担当"""

from typing import Dict, Any, List, Optional
from utils.logger import get_logger

# DefaultStoryGeneratorはConversionServiceに統合済み
from exceptions.custom_errors import ConversionError
from ifcCreator.core.element_creation_factory import ElementCreationFactory
from ifcCreator.core.ifc_project_builder import IFCProjectBuilder

# ElementTrackerはElementCreationFactoryに統合済み


class IfcGenerationService:
    """IFCファイル生成を担当するサービス"""

    def __init__(
        self, logger=None, project_creator_service=None, conversion_service=None
    ):
        self.logger = logger or get_logger(__name__)
        # project_creator_serviceは下位互換性のため残すが、統合済み機能を使用
        # DefaultStoryGenerator機能はconversion_serviceから取得
        self.conversion_service = conversion_service

    def has_structural_elements(self, conversion_result: Dict[str, Any]) -> bool:
        """構造要素が存在するかチェック"""
        element_keys = [
            "beam_defs",
            "column_defs",
            "brace_defs",
            "pile_defs",
            "slab_defs",
            "wall_defs",
            "footing_defs",
            "foundation_column_defs",
        ]

        for key in element_keys:
            if conversion_result.get(key):
                return True
        return False

    def create_ifc_file(
        self, conversion_result: Dict[str, Any], output_filename: str, stb_content: str
    ) -> bool:
        """変換結果からIFCファイルを生成"""

        if not self.has_structural_elements(conversion_result):
            self.logger.warning("ST-Bridge ファイルに構造要素が見つかりませんでした")
            return False

        self.logger.info("--- 統合IFCファイルを生成中 ---")  # 各要素定義を取得
        beam_defs = conversion_result.get("beam_defs", [])
        column_defs = conversion_result.get("column_defs", [])
        brace_defs = conversion_result.get("brace_defs", [])
        pile_defs = conversion_result.get("pile_defs", [])
        slab_defs = conversion_result.get("slab_defs", [])
        wall_defs = conversion_result.get("wall_defs", [])
        footing_defs = conversion_result.get("footing_defs", [])
        foundation_column_defs = conversion_result.get("foundation_column_defs", [])
        story_defs = conversion_result.get("story_defs", [])
        axes_defs = conversion_result.get("axes_defs", [])

        try:
            return self._generate_ifc_with_stories(
                story_defs,
                beam_defs,
                column_defs,
                brace_defs,
                pile_defs,
                slab_defs,
                wall_defs,
                footing_defs,
                foundation_column_defs,
                axes_defs,
                output_filename,
                stb_content,
            )
        except Exception as e:
            self.logger.error("IFC ファイル生成中に例外が発生しました: %s", e)
            import traceback

            self.logger.error("トレースバック: %s", traceback.format_exc())
            raise

    def _generate_ifc_with_stories(
        self,
        story_defs,
        beam_defs,
        column_defs,
        brace_defs,
        pile_defs,
        slab_defs,
        wall_defs,
        footing_defs,
        foundation_column_defs,
        axes_defs,
        output_filename,
        stb_content,
    ) -> bool:
        """階層を含むIFC生成"""

        try:
            from ifcCreator.core.ifc_project_builder import IFCProjectBuilder
            from ifcCreator.core.story_converter import StbToIfcStoryConverter

            # プロジェクト構造を作成
            builder = IFCProjectBuilder()
            builder.create_project_structure()

            # Storyデータがない場合はデフォルトStoryを生成
            if self._should_use_default_story(story_defs):
                self.logger.info(
                    "デフォルトStory 'GL' を生成して統合処理を実行します..."
                )
                story_defs = self._create_default_story(
                    beam_defs=beam_defs,
                    column_defs=column_defs,
                    brace_defs=brace_defs,
                    pile_defs=pile_defs,
                    slab_defs=slab_defs,
                    wall_defs=wall_defs,
                    footing_defs=footing_defs,
                    foundation_column_defs=foundation_column_defs,
                )

            # 要素定義の階情報をデフォルト Story 名に統一（デフォルト Story のみの場合）
            if story_defs and builder.file:
                if (
                    len(story_defs) == 1
                    and story_defs[0].get("story_type") == "DEFAULT"
                ):
                    default_floor = story_defs[0].get("name")
                    for defs in (
                        beam_defs,
                        column_defs,
                        brace_defs,
                        pile_defs,
                        slab_defs,
                        wall_defs,
                        footing_defs,
                        foundation_column_defs,
                    ):
                        for d in defs:
                            d["floor"] = default_floor
                return self._convert_stories_and_elements(
                    builder,
                    story_defs,
                    stb_content,
                    output_filename,
                    beam_defs,
                    column_defs,
                    brace_defs,
                    pile_defs,
                    slab_defs,
                    wall_defs,
                    footing_defs,
                    foundation_column_defs,
                    axes_defs,
                )
            else:
                return self._fallback_generation(
                    output_filename,
                    beam_defs,
                    column_defs,
                    brace_defs,
                    pile_defs,
                    slab_defs,
                    wall_defs,
                    footing_defs,
                    foundation_column_defs,
                )
        except ImportError as e:
            self.logger.error("必要なモジュールのインポートに失敗しました: %s", e)
            return self._fallback_generation(
                output_filename,
                beam_defs,
                column_defs,
                brace_defs,
                pile_defs,
                slab_defs,
                wall_defs,
                footing_defs,
                foundation_column_defs,
            )
        except ImportError as e:
            self.logger.error("必要なモジュールのインポートに失敗しました: %s", e)
            return self._fallback_generation(
                output_filename,
                beam_defs,
                column_defs,
                brace_defs,
                pile_defs,
                slab_defs,
                wall_defs,
                footing_defs,
                foundation_column_defs,
            )

    def _convert_stories_and_elements(
        self,
        builder,
        story_defs,
        stb_content,
        output_filename,
        beam_defs,
        column_defs,
        brace_defs,
        pile_defs,
        slab_defs,
        wall_defs,
        footing_defs,
        foundation_column_defs,
        axes_defs,
    ) -> bool:
        """階層と要素の変換処理"""

        # 必要なクラスをインポート
        from ifcCreator.core.story_converter import StbToIfcStoryConverter

        story_source = (
            "既存のSTB Story"
            if len(story_defs) > 1 or story_defs[0].get("story_type") != "DEFAULT"
            else "デフォルトStory"
        )

        self.logger.info(f"{story_source}変換開始: {len(story_defs)}階層を処理中...")

        converter = StbToIfcStoryConverter(builder, stb_content)

        # 節点IDと階名の対応辞書を作成
        node_story_map = {}
        for sd in story_defs:
            for nid in sd.get("node_ids", []):
                node_story_map[nid] = sd.get("name")

        converter.set_node_story_map(node_story_map)
        converter.set_element_definitions(
            {
                "beam_defs": beam_defs,
                "column_defs": column_defs,
                "brace_defs": brace_defs,
                "pile_defs": pile_defs,
                "slab_defs": slab_defs,
                "wall_defs": wall_defs,
                "footing_defs": footing_defs,
                "foundation_column_defs": foundation_column_defs,
            }
        )

        # Step 1: 全階層の作成
        self.logger.info("Step 1: 階層構造を作成中...")
        for story_def in story_defs:
            story_name = story_def.get("name", "Unknown")
            self.logger.info(f"階層 '{story_name}' を作成中...")
            converter.convert_stb_story_to_ifc_story(story_def)

        # Step 2: 通芯の作成（要素作成前）
        if axes_defs:
            self.logger.info(f"Step 2: 通芯を作成中: {len(axes_defs)}グループ")
            self._convert_grid_axes(builder, axes_defs)

        # Step 3: 各階層の要素作成
        self.logger.info("Step 3: 構造要素を作成中...")
        for story_def in story_defs:
            story_name = story_def.get("name", "Unknown")
            self.logger.info(f"階層 '{story_name}' の要素を作成中...")
            converter.convert_elements_for_story(story_def)

        # 要素関連付けとファイル出力
        converter.associate_elements_to_storeys()
        builder.file.write(output_filename)

        self.logger.info(
            "ストーリー階層と要素を含むIFCを生成しました: %s", output_filename
        )
        self._log_element_summary(
            beam_defs,
            column_defs,
            brace_defs,
            pile_defs,
            slab_defs,
            wall_defs,
            footing_defs,
            foundation_column_defs,
        )
        return True

    def _convert_grid_axes(self, builder, axes_defs: List[Dict]) -> None:
        """通芯をIfcGridに変換"""
        try:
            from ifcCreator.specialized.grid_creator import (
                IFCGridCreator,
                GridDefinitionProcessor,
            )

            # 通芯定義を処理
            processor = GridDefinitionProcessor()
            processed_axes = processor.process(axes_defs)

            if not processed_axes:
                self.logger.warning("処理可能な通芯グループがありません")
                return

            # IFCGridCreatorを初期化してbuilderを設定
            self.logger.info("IFCGridCreatorを初期化中")
            try:
                grid_creator = IFCGridCreator()
                self.logger.info("GridCreator作成完了")
                grid_creator.project_builder = builder
                self.logger.info("プロジェクトビルダー設定完了")
            except Exception as e:
                self.logger.error("GridCreator初期化エラー: %s", e)
                import traceback

                self.logger.error("トレースバック: %s", traceback.format_exc())
                return

            # IfcGridを作成
            self.logger.info("IfcGrid作成を開始")
            grid = grid_creator.create_grid_from_axes_groups(processed_axes)
            self.logger.info("IfcGrid作成処理完了")

            if grid:
                self.logger.info("IfcGrid作成完了")
            else:
                self.logger.warning("IfcGrid作成に失敗しました")

        except Exception as e:
            self.logger.error("通芯変換中にエラーが発生: %s", e)
            import traceback

            self.logger.error("トレースバック: %s", traceback.format_exc())

    def _fallback_generation(
        self,
        output_filename,
        beam_defs,
        column_defs,
        brace_defs,
        pile_defs,
        slab_defs,
        wall_defs,
        footing_defs,
        foundation_column_defs,
    ) -> bool:
        """フォールバック処理（統合済みプロジェクト作成機能を使用）"""

        self.logger.warning(
            "IFCプロジェクトビルダーの初期化に失敗しました。統合済み方式で変換します..."
        )

        return self._create_combined_ifc_project(
            output_filename,
            beam_defs,
            column_defs,
            brace_defs,
            pile_defs,
            slab_defs,
            wall_defs,
            footing_defs,
            foundation_column_defs,
        )

    def _create_combined_ifc_project(
        self,
        filename: str,
        beam_defs: List[Dict[str, Any]],
        column_defs: List[Dict[str, Any]],
        brace_defs: Optional[List[Dict[str, Any]]] = None,
        pile_defs: Optional[List[Dict[str, Any]]] = None,
        slab_defs: Optional[List[Dict[str, Any]]] = None,
        wall_defs: Optional[List[Dict[str, Any]]] = None,
        footing_defs: Optional[List[Dict[str, Any]]] = None,
        foundation_column_defs: Optional[List[Dict[str, Any]]] = None,
        project_name: str = "ST-Bridge Combined Project",
    ) -> bool:
        """梁・柱・ブレースをまとめてIFCファイルを生成（ProjectCreatorServiceから統合）"""

        try:
            # プロジェクトビルダーとファクトリーを初期化（要素追跡機能統合済み）
            project_builder = IFCProjectBuilder()
            project_builder.create_project_structure(project_name)
            element_creator = ElementCreationFactory(project_builder)

            # 要素がある場合のみそれぞれの作成処理を実行
            if beam_defs:
                element_creator.create_beams(beam_defs)

            if column_defs:
                element_creator.create_columns(column_defs)

            if brace_defs:
                element_creator.create_braces(brace_defs)

            if pile_defs:
                element_creator.create_piles(pile_defs)

            if slab_defs:
                element_creator.create_slabs(slab_defs)

            if wall_defs:
                element_creator.create_walls(wall_defs)

            if footing_defs:
                element_creator.create_footings(footing_defs)

            if foundation_column_defs:
                element_creator.create_foundation_columns(foundation_column_defs)

            # ファイルを保存
            if project_builder.file:
                project_builder.file.write(filename)
                return True
            else:
                raise ConversionError("IFCファイルが正しく初期化されませんでした")

        except Exception as e:
            error_msg = f"IFCプロジェクト作成中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            raise ConversionError(error_msg) from e

    def _log_element_summary(
        self,
        beam_defs,
        column_defs,
        brace_defs,
        pile_defs,
        slab_defs,
        wall_defs,
        footing_defs,
        foundation_column_defs,
    ):
        """要素サマリーログ出力"""
        self.logger.info("  - 梁: %d", len(beam_defs))
        self.logger.info("  - 柱: %d", len(column_defs))
        self.logger.info("  - ブレース: %d", len(brace_defs))
        self.logger.info("  - 杭: %d", len(pile_defs))
        self.logger.info("  - スラブ: %d", len(slab_defs))
        self.logger.info("  - 壁: %d", len(wall_defs))
        self.logger.info("  - フーチング: %d", len(footing_defs))
        self.logger.info("  - 基礎柱: %d", len(foundation_column_defs))

    # === DefaultStoryGenerator機能（統合済み - フォールバック実装） ===

    def _should_use_default_story(self, story_defs: list) -> bool:
        """デフォルトStoryを使用すべきかどうかを判定（ConversionServiceから利用できない場合のフォールバック）"""
        if self.conversion_service:
            return self.conversion_service.should_use_default_story(story_defs)

        # フォールバック実装
        if not story_defs:
            self.logger.info("Story定義がないため、デフォルトStoryを使用します")
            return True

        if len(story_defs) == 0:
            self.logger.info("Story定義が空のため、デフォルトStoryを使用します")
            return True  # 有効なStory定義が存在する場合
        valid_stories = [
            story for story in story_defs if story.get("name") and story.get("node_ids")
        ]

        if not valid_stories:
            self.logger.info("有効なStory定義がないため、デフォルトStoryを使用します")
            return True

        self.logger.info(f"既存のStory定義を使用します: {len(valid_stories)}個の階層")
        return False

    def _create_default_story(
        self,
        beam_defs: list = None,
        column_defs: list = None,
        brace_defs: list = None,
        pile_defs: list = None,
        slab_defs: list = None,
        wall_defs: list = None,
        footing_defs: list = None,
        foundation_column_defs: list = None,
    ) -> list:
        """デフォルトStoryを生成（ConversionServiceから利用できない場合のフォールバック）"""
        if self.conversion_service:
            return self.conversion_service.create_default_story(
                beam_defs=beam_defs,
                column_defs=column_defs,
                brace_defs=brace_defs,
                pile_defs=pile_defs,
                slab_defs=slab_defs,
                wall_defs=wall_defs,
                footing_defs=footing_defs,
                foundation_column_defs=foundation_column_defs,
            )

        # フォールバック実装（簡易版）
        self.logger.warning(
            "ConversionServiceが利用できないため、簡易的なデフォルトStoryを生成します"
        )

        default_story = {
            "name": "GL",
            "height": 3000.0,
            "elevation": 0.0,
            "node_ids": [],  # 簡易版では空のnode_idsを使用
            "story_type": "DEFAULT",
        }

        return [default_story]
