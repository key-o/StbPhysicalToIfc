"""基礎要素（フーチング）の生成クリエーター"""

from typing import Dict, List
from .base_element_creator import BaseElementCreator, logger


class FoundationElementCreator(BaseElementCreator):
    """基礎要素の生成を担当するクリエーター"""

    def create_footings(self, footing_defs: List[Dict]) -> List:
        """フーチング要素を生成

        Args:
            footing_defs: フーチング定義のリスト

        Returns:
            生成されたフーチング要素のリスト
        """
        if not footing_defs:
            return []

        created_elements = []
        self._log_creation_start("フーチング", len(footing_defs))

        try:
            footing_creator, processor = self._initialize_footing_creator()
            self._log_creator_initialized("フーチング")

            for i, fdef in enumerate(footing_defs):
                try:
                    # 定義を処理
                    processed_def = processor.process_footing_definition(fdef, i)

                    # フーチングを生成
                    footing = footing_creator.create_footing(
                        processed_def["bottom_point"],
                        processed_def["top_point"],
                        processed_def["section"],
                        processed_def["name"],
                        processed_def["tag"],
                        processed_def["stb_guid"],
                    )

                    if footing:
                        created_elements.append(footing)
                        self._track_created_element(fdef, footing)
                        self._log_element_success("フーチング", i, footing)
                    else:
                        self._log_element_failure("フーチング", i)

                except ValueError as e:
                    footing_name = fdef.get("name", "N/A")
                    logger.error(
                        "フーチング %d (名前: %s) の作成でエラー: %s",
                        i,
                        footing_name,
                        e,
                    )
                except Exception as e:
                    footing_name = fdef.get("name", "N/A")
                    logger.exception(
                        "フーチング %d (名前: %s) の作成中に予期せぬエラー: %s",
                        i,
                        footing_name,
                        e,
                    )

            success_count = self._count_successful_elements(
                created_elements, "IfcFooting"
            )
            self._log_creation_complete(
                "フーチング", success_count, len(footing_defs), "IfcFooting"
            )

        except Exception as e:
            self._log_creator_init_error("フーチング", e)

        return created_elements

    def create_footing_project_with_coordinates(
        self, filename: str, footing_defs: List[Dict], project_name: str
    ):
        """フーチング専用プロジェクト作成（統合された実装）"""
        from ifcCreator.footing import create_footing_project_with_coordinates as _impl
        from exceptions.custom_errors import ConversionError

        try:
            return _impl(filename, footing_defs, project_name)
        except Exception as e:
            error_msg = f"フーチングプロジェクト作成中にエラーが発生しました: {e}"
            logger.error(error_msg)
            raise ConversionError(error_msg) from e

    def create_elements(self, element_defs: List[Dict]) -> List:
        """要素を生成（基底クラスの抽象メソッド実装）"""
        # この実装では具体的な要素タイプが必要なため、直接呼び出されることは想定していない
        raise NotImplementedError(
            "Specific element type creation method should be called"
        )

    def _initialize_footing_creator(self):
        """フーチングCreatorを初期化"""
        from ifcCreator.footing_creator import IFCFootingCreator
        from ifcCreator.unified_definition_processor import (
            UnifiedDefinitionProcessor,
        )

        footing_creator = IFCFootingCreator()
        footing_creator.project_builder = self.project_builder

        # 必要なマネージャを初期化
        footing_creator.profile_factory = footing_creator.profile_factory_cls(self.file)
        footing_creator.type_manager = footing_creator.type_manager_cls(
            self.file, self.owner_history, footing_creator.profile_factory
        )
        footing_creator.geometry_builder = footing_creator.geometry_builder_cls(
            self.file,
            self.project_builder.model_context,
            footing_creator.profile_factory,
        )
        footing_creator.property_manager = footing_creator.property_manager_cls(
            self.file, self.owner_history
        )

        processor = UnifiedDefinitionProcessor()
        return footing_creator, processor

    def create_foundation_columns(self, foundation_column_defs: List[Dict]) -> List:
        """基礎柱要素を生成

        Args:
            foundation_column_defs: 基礎柱定義のリスト

        Returns:
            生成された基礎柱要素のリスト
        """
        if not foundation_column_defs:
            return []

        created_elements = []
        self._log_creation_start("基礎柱", len(foundation_column_defs))

        try:
            foundation_column_creator = self._initialize_foundation_column_creator()
            self._log_creator_initialized("基礎柱")

            for i, fcdef in enumerate(foundation_column_defs):
                try:  # 基礎柱を生成
                    foundation_column = (
                        foundation_column_creator.create_foundation_column(
                            fcdef, self.project_builder.storey, self.file
                        )
                    )

                    if foundation_column:
                        created_elements.append(foundation_column)
                        self._track_created_element(fcdef, foundation_column)
                        self._log_element_success("基礎柱", i, foundation_column)
                    else:
                        self._log_element_failure("基礎柱", i)

                except Exception as e:
                    self._log_element_creation_error("基礎柱", i, e)

        except Exception as e:
            self._log_creator_init_error("基礎柱", e)

        success_count = self._count_successful_elements(created_elements, "IfcColumn")
        self._log_creation_complete(
            "基礎柱", success_count, len(foundation_column_defs), "IfcColumn"
        )
        return created_elements

    def _initialize_foundation_column_creator(self):
        """基礎柱作成器を初期化"""
        from ifcCreator.foundation_column_creator import (
            IFCFoundationColumnCreator,
        )

        foundation_column_creator = IFCFoundationColumnCreator()
        foundation_column_creator.project_builder = self.project_builder

        # 必要なマネージャを初期化（柱ベースの実装を使用）
        foundation_column_creator.profile_factory = (
            foundation_column_creator.profile_factory_cls(self.file)
        )
        foundation_column_creator.type_manager = (
            foundation_column_creator.type_manager_cls(
                self.file, self.owner_history, foundation_column_creator.profile_factory
            )
        )
        foundation_column_creator.geometry_builder = (
            foundation_column_creator.geometry_builder_cls(
                self.file,
                self.project_builder.model_context,
                foundation_column_creator.profile_factory,
            )
        )
        foundation_column_creator.property_manager = (
            foundation_column_creator.property_manager_cls(
                self.file, self.owner_history
            )
        )

        return foundation_column_creator
