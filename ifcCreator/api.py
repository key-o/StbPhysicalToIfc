# ifcCreator/api.py
"""
IfcCreator Simplified High-Level API
複雑な抽象化を排除した直接的な実装
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class IfcCreator:
    """簡素化されたIfcCreator高レベルAPI

    複雑なFactoryパターンを排除し、直接的な実装で高速化

    使用例:
        IfcCreator.create_building_project(
            "building.ifc",
            {
                "columns": column_definitions,
                "beams": beam_definitions,
                "walls": wall_definitions,
                "slabs": slab_definitions
            },
            "マイ建物プロジェクト"
        )
    """

    @staticmethod
    def create_building_project(
        filename: str,
        element_definitions: Dict[str, List[Dict[str, Any]]],
        project_name: str = "建物プロジェクト",
    ):
        """統合建物プロジェクトを作成（簡素化版）

        Args:
            filename: 出力IFCファイル名
            element_definitions: 要素定義の辞書
            project_name: プロジェクト名

        Returns:
            作成されたIFCファイルオブジェクト
        """
        from ifcCreator.ifc_project_builder import IFCProjectBuilder
        
        logger.info(f"簡素化建物プロジェクト '{project_name}' の作成を開始します")

        # プロジェクト構造を作成
        project_builder = IFCProjectBuilder()
        project_builder.create_project_structure(project_name)

        total_created = 0
        element_summary = {}

        # 各要素タイプを順次処理（簡素化版Creator使用）
        if "beams" in element_definitions:
            beam_defs = element_definitions["beams"]
            logger.info(f"梁を処理中... ({len(beam_defs)}個)")
            count = IfcCreator._process_beams_simple(project_builder, beam_defs)
            total_created += count
            element_summary["梁"] = count

        # 他の要素タイプは既存Creatorを使用（段階的移行）
        if "columns" in element_definitions:
            column_defs = element_definitions["columns"]
            logger.info(f"柱を処理中... ({len(column_defs)}個)")
            count = IfcCreator._process_columns(project_builder, column_defs)
            total_created += count
            element_summary["柱"] = count

        if "braces" in element_definitions:
            brace_defs = element_definitions["braces"]
            logger.info(f"ブレースを処理中... ({len(brace_defs)}個)")
            count = IfcCreator._process_braces(project_builder, brace_defs)
            total_created += count
            element_summary["ブレース"] = count

        # サマリーログ
        logger.info(f"簡素化プロジェクト作成完了:")
        logger.info(f"  総要素数: {total_created}")
        for element_type, count in element_summary.items():
            logger.info(f"  {element_type}: {count}個")

        if project_builder.file:
            project_builder.file.write(filename)
            logger.info(f"IFCファイルを保存しました: {filename}")
        return project_builder.file

    @staticmethod
    def _process_beams_simple(project_builder, beam_defs):
        """梁のバッチ処理（統一Creator使用）"""
        # Note: beam_creator not available, using refactored version
        # from ifcCreator.beam_creator_refactored import IFCBeamCreatorRefactored as IFCBeamCreator
        
        creator = IFCBeamCreator()
        creator.project_builder = project_builder
        
        created_count = 0
        for i, definition in enumerate(beam_defs):
            try:
                processed = IFCBeamCreator.process_beam_definition(definition, i)
                creator.create_beam(
                    processed["start_point"],
                    processed["end_point"],
                    processed["sec_start"],
                    processed["sec_end"],
                    processed["name"],
                    processed["tag"],
                    processed.get("stb_guid"),
                )
                created_count += 1
            except Exception as e:
                logger.warning(f"梁 {i} をスキップ: {e}")
        return created_count

    @staticmethod
    def _process_columns(project_builder, column_defs):
        """柱のバッチ処理（既存版）"""
        # Note: column_creator not available, using refactored version
        # from ifcCreator.column_creator_refactored import IFCColumnCreatorRefactored as IFCColumnCreator
        
        creator = IFCColumnCreator()
        creator.project_builder = project_builder
        
        created_count = 0
        for i, definition in enumerate(column_defs):
            try:
                processed = IFCColumnCreator.process_column_definition(definition, i)
                creator.create_column(
                    processed["bottom_point"],
                    processed["top_point"],
                    processed["sec_bottom"],
                    processed["sec_top"],
                    processed["name"],
                    processed["tag"],
                    processed.get("rotation_radians", 0.0),
                    processed.get("is_reference_direction", False),
                    processed.get("stb_guid"),
                )
                created_count += 1
            except Exception as e:
                logger.warning(f"柱 {i} をスキップ: {e}")
        return created_count

    @staticmethod
    def _process_braces(project_builder, brace_defs):
        """ブレースのバッチ処理（既存版）"""
        from ifcCreator.brace_creator_refactored import IFCBraceCreatorRefactored as IFCBraceCreator
        
        creator = IFCBraceCreator()
        creator.project_builder = project_builder
        
        created_count = 0
        for i, definition in enumerate(brace_defs):
            try:
                processed = IFCBraceCreator.process_brace_definition(definition, i)
                creator.create_brace(
                    processed["start_point"],
                    processed["end_point"],
                    processed["sec_start"],
                    processed["sec_end"],
                    processed["name"],
                    processed["tag"],
                    processed.get("stb_guid"),
                )
                created_count += 1
            except Exception as e:
                logger.warning(f"ブレース {i} をスキップ: {e}")
        return created_count
