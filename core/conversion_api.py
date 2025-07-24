"""STB to IFC変換専用API

UIとは独立した変換機能を提供します。
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# 新アーキテクチャ準備完了、現在はConversionServiceを使用
from core.conversion_service import ConversionService
from config.settings import AppConfig
from exceptions.custom_errors import (
    Stb2IfcError,
    ConversionError,
    FileNotFoundError,
    IFCGenerationError,
)


class Stb2IfcConverter:
    """STB to IFC変換専用クラス

    UI層から独立した変換機能を提供します。
    """

    def __init__(self, debug_enabled: bool = False):
        """初期化

        Args:
            debug_enabled: デバッグモードの有効/無効
        """
        self.debug_enabled = debug_enabled
        self._orchestrator = None
        self._logger = None
        self._is_initialized = False

    def initialize(self) -> None:
        """変換サービスを初期化"""
        if self._is_initialized:
            return

        # 設定とロガーの初期化（常に実行）
        config = AppConfig()
        config.debug_enabled = self.debug_enabled

        # ロガー設定
        logger = logging.getLogger("stb2ifc_api")
        logger.setLevel(logging.DEBUG if self.debug_enabled else logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        self._logger = logger

        try:
            # ConversionOrchestratorを直接初期化
            from core.conversion_orchestrator import ConversionOrchestrator

            self._orchestrator = ConversionOrchestrator()
            self._logger.info("変換APIが初期化されました")

        except ImportError as e:
            # フォールバック: ConversionServiceを直接使用
            self._orchestrator = None
            from core.conversion_service import ConversionService

            self._conversion_service = ConversionService(
                self._logger, self.debug_enabled
            )
            error_msg = f"ConversionOrchestrator読み込みエラー、ConversionServiceにフォールバック: {e}"
            self._logger.warning(error_msg)
        except Exception as e:
            error_msg = f"初期化エラー: {e}"
            self._logger.error(error_msg)
            raise Stb2IfcError(error_msg) from e

        self._is_initialized = True

    def convert_file(
        self, stb_file_path: str, output_file_path: Optional[str] = None, selected_categories: Optional[List[str]] = None
    ) -> str:
        """STBファイルをIFCファイルに変換

        Args:
            stb_file_path: 入力STBファイルパス
            output_file_path: 出力IFCファイルパス（省略時は自動生成）
            selected_categories: 変換対象カテゴリリスト（None=全て変換）

        Returns:
            str: 生成されたIFCファイルのパス

        Raises:
            Stb2IfcError: 変換エラー
        """
        self.initialize()

        try:
            # パスの検証
            stb_path = Path(stb_file_path)
            if not stb_path.exists():
                raise FileNotFoundError(f"STBファイルが見つかりません: {stb_file_path}")

            # 出力パスの生成
            if output_file_path is None:
                output_file_path = str(stb_path.with_suffix(".ifc"))

            self._logger.info("変換開始: %s -> %s", stb_file_path, output_file_path)

            # カテゴリ選択を設定
            if selected_categories:
                self._logger.info(f"変換対象カテゴリ: {', '.join(selected_categories)}")

            # ConversionOrchestratorまたはConversionServiceを使用
            if self._orchestrator:
                # ConversionOrchestratorの場合、カテゴリ設定は今後のバージョンで実装
                result = self._orchestrator.convert(stb_file_path, output_file_path)

                if not result.success:
                    error_msg = "IFCファイルの生成に失敗しました"
                    if result.errors:
                        error_msg += f": {'; '.join(result.errors)}"
                    raise Stb2IfcError(error_msg)
            else:
                # フォールバック: ConversionServiceを直接使用
                # カテゴリを設定
                self._conversion_service.set_selected_categories(selected_categories)
                
                stb_content = self._conversion_service.load_stb_file(stb_file_path)
                conversion_result = self._conversion_service.convert_stb_to_ifc(
                    stb_content, stb_file_path
                )
                success = self._conversion_service.create_ifc_file(
                    conversion_result, output_file_path
                )

                if not success:
                    raise Stb2IfcError("IFCファイルの生成に失敗しました")

            self._logger.info("変換完了: %s", output_file_path)
            return output_file_path

        except (FileNotFoundError, ConversionError, IFCGenerationError) as e:
            error_msg = f"変換エラー: {e}"
            self._logger.error(error_msg)
            raise Stb2IfcError(error_msg) from e
        except IOError as e:
            error_msg = f"ファイル入出力エラー: {e}"
            self._logger.error(error_msg)
            raise Stb2IfcError(error_msg) from e

    def convert_data(self, stb_xml_content: str, output_file_path: str) -> str:
        """STB XMLデータをIFCファイルに変換

        Args:
            stb_xml_content: STB XMLデータ
            output_file_path: 出力IFCファイルパス

        Returns:
            str: 生成されたIFCファイルのパス

        Raises:
            Stb2IfcError: 変換エラー
        """
        self.initialize()

        try:
            self._logger.info("データ変換開始: -> %s", output_file_path)

            # ConversionServiceを直接使用
            conversion_service = self._conversion_service

            # STB to IFC変換
            conversion_result = conversion_service.convert_stb_to_ifc(
                stb_xml_content, "memory_data"
            )

            # IFCファイル生成
            success = conversion_service.create_ifc_file(
                conversion_result, output_file_path
            )

            if not success:
                raise Stb2IfcError("IFCファイルの生成に失敗しました")

            self._logger.info("データ変換完了: %s", output_file_path)
            return output_file_path

        except (ConversionError, IFCGenerationError) as e:
            error_msg = f"データ変換エラー: {e}"
            self._logger.error(error_msg)
            raise Stb2IfcError(error_msg) from e
        except IOError as e:
            error_msg = f"ファイル出力エラー: {e}"
            self._logger.error(error_msg)
            raise Stb2IfcError(error_msg) from e

    def get_conversion_info(self, stb_file_path: str, selected_categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """STBファイルの変換情報を取得（変換は行わない）

        Args:
            stb_file_path: STBファイルパス
            selected_categories: 変換対象カテゴリリスト（None=全て変換）

        Returns:
            Dict[str, Any]: 変換情報
        """
        self.initialize()

        try:
            # ConversionServiceを使用（OrchestratorまたはConversionServiceを使用）
            if self._orchestrator:
                # Orchestratorがある場合はそれを使用
                from core.conversion_service import ConversionService

                conversion_service = ConversionService(self._logger, self.debug_enabled)
            else:
                # フォールバック時の_conversion_serviceを使用
                conversion_service = self._conversion_service

            # カテゴリを設定
            conversion_service.set_selected_categories(selected_categories)

            # STBファイル読み込み（統合済み機能を使用）
            stb_xml_content = conversion_service.load_stb_file(stb_file_path)

            # 変換情報の取得（実際の変換は行わない）
            conversion_result = conversion_service.convert_stb_to_ifc(
                stb_xml_content, stb_file_path
            )

            # 統計情報を作成
            info = {"input_file": stb_file_path, "element_counts": {}}

            for element_type, elements in conversion_result.items():
                try:
                    count = len(elements) if hasattr(elements, "__len__") else 0
                    info["element_counts"][element_type] = count
                except (TypeError, AttributeError) as e:
                    self._logger.warning(
                        f"要素カウント取得エラー ({element_type}): {e}"
                    )
                    info["element_counts"][element_type] = "N/A"

            return info

        except (FileNotFoundError, ConversionError) as e:
            error_msg = f"変換情報取得エラー: {e}"
            self._logger.error(error_msg)
            raise Stb2IfcError(error_msg) from e
        except IOError as e:
            error_msg = f"ファイル読み込みエラー: {e}"
            self._logger.error(error_msg)
            raise Stb2IfcError(error_msg) from e
