# unified_stb_parser.py
from abc import ABC, abstractmethod
from typing import List, Dict, Type, Optional
import xml.etree.ElementTree as ET
from enum import Enum

from .xml_parser import STBXMLParser
from .node_extractor import NodeExtractor
from common.xml_utils import XMLUtils
from utils.logger import get_logger

logger = get_logger(__name__)


class ElementType(Enum):
    """構造要素タイプの列挙"""

    BEAM = "beam"
    COLUMN = "column"
    BRACE = "brace"
    WALL = "wall"
    SLAB = "slab"
    FOOTING = "footing"
    PILE = "pile"
    FOUNDATION_COLUMN = "foundation_column"
    SRC = "src"
    STORY = "story"
    AXES = "axes"


class ExtractorConfig:
    """抽出器設定クラス"""

    # 各要素タイプに対応する抽出器とセクション抽出器のマッピング
    EXTRACTOR_MAPPING = {
        ElementType.BEAM: {
            "extractor": "beam_extractor.BeamExtractor",
            "section_extractor": "beam_section_extractor.BeamSectionExtractor",
            "extract_method": "extract_beams",
        },
        ElementType.COLUMN: {
            "extractor": "column_extractor.ColumnExtractor",
            "section_extractor": "column_section_extractor.ColumnSectionExtractor",
            "extract_method": "extract_columns",
        },
        ElementType.BRACE: {
            "extractor": "brace_extractor.BraceExtractor",
            "section_extractor": "brace_section_extractor.BraceSectionExtractor",
            "extract_method": "extract_braces",
        },
        ElementType.WALL: {
            "extractor": "wall_extractor.WallExtractor",
            "section_extractor": "wall_section_extractor.WallSectionExtractor",
            "extract_method": "extract_walls",
        },
        ElementType.SLAB: {
            "extractor": "slab_extractor.SlabExtractor",
            "section_extractor": "slab_section_extractor.SlabSectionExtractor",
            "extract_method": "extract_slabs",
        },
        ElementType.FOOTING: {
            "extractor": "footing_extractor.FootingExtractor",
            "section_extractor": "footing_section_extractor.FootingSectionExtractor",
            "extract_method": "extract_footings",
        },
        ElementType.PILE: {
            "extractor": "pile_extractor.PileExtractor",
            "section_extractor": "pile_section_extractor.PileSectionExtractor",
            "extract_method": "extract_piles",
        },
        ElementType.FOUNDATION_COLUMN: {
            "extractor": "foundation_column_extractor.FoundationColumnExtractor",
            "section_extractor": "column_section_extractor.ColumnSectionExtractor",
            "extract_method": "extract_foundation_columns",
        },
        ElementType.SRC: {
            "extractor": None,  # Special handling - direct section processing
            "section_extractor": "src_section_extractor.SRCSectionExtractor",
            "extract_method": "extract_src_sections",
        },
        ElementType.STORY: {
            "extractor": None,  # Special handling
            "section_extractor": None,
            "extract_method": "parse_stories",
        },
        ElementType.AXES: {
            "extractor": "axes_extractor.AxesExtractor",
            "section_extractor": None,
            "extract_method": "extract_axes",
        },
    }


class UnifiedSTBParser:
    """統合ST-Bridgeパーサー - 全構造要素の解析を統一的に処理"""

    def __init__(self, stb_xml_string: str):
        """
        Args:
            stb_xml_string: ST-Bridge XMLファイルの内容
        """
        self.stb_xml_string = stb_xml_string
        self.xml_parser = STBXMLParser(stb_xml_string)
        self._parsed_data = {}
        self._is_parsed = False

    def _parse_xml(self) -> bool:
        """XML解析の初期化（共通処理）"""
        if self._is_parsed:
            return True

        if not self.xml_parser.parse():
            logger.debug("XML解析に失敗しました")
            return False

        self._is_parsed = True
        return True

    def _get_extractor_class(self, module_path: str):
        """動的に抽出器クラスを取得"""
        try:
            module_name, class_name = module_path.rsplit(".", 1)
            module = __import__(f"stbParser.{module_name}", fromlist=[class_name])
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"抽出器クラスの取得に失敗: {module_path}, エラー: {e}")
            return None

    def parse_element_type(self, element_type: ElementType) -> List[Dict]:
        """指定された要素タイプの解析を実行

        Args:
            element_type: 解析する構造要素タイプ

        Returns:
            解析結果の辞書リスト
        """
        if not self._parse_xml():
            return []

        # キャッシュされた結果があれば返す
        if element_type in self._parsed_data:
            return self._parsed_data[element_type]

        try:
            config = ExtractorConfig.EXTRACTOR_MAPPING.get(element_type)
            if not config:
                logger.error(f"未対応の要素タイプ: {element_type}")
                return []

            # 特殊処理（Story、SRC）- 直接処理して循環importを回避
            if config["extractor"] is None:
                if element_type == ElementType.STORY:
                    element_defs = self._parse_stories_direct()
                elif element_type == ElementType.SRC:
                    element_defs = self._parse_src_sections_direct()
                else:
                    element_defs = []

                self._parsed_data[element_type] = element_defs
                logger.debug(f"{element_type.value} 定義数: {len(element_defs)}")
                return element_defs

            # 共通データの取得
            node_extractor = NodeExtractor(self.xml_parser)
            nodes_data = node_extractor.extract_nodes()

            # セクション抽出器の初期化（必要な場合のみ）
            sections_data = []
            if config["section_extractor"]:
                section_extractor_class = self._get_extractor_class(
                    config["section_extractor"]
                )
                if section_extractor_class:
                    section_extractor = section_extractor_class(self.xml_parser)
                    sections_data = section_extractor.extract_sections()

            # 要素抽出器の初期化と実行
            extractor_class = self._get_extractor_class(config["extractor"])
            if not extractor_class:
                return []

            extractor = extractor_class(self.xml_parser)
            extract_method = getattr(extractor, config["extract_method"])

            # メソッドの引数に応じて呼び出し
            if config["section_extractor"]:
                element_defs = extract_method(nodes_data, sections_data)
            elif element_type == ElementType.AXES:
                # Axes抽出器は特殊でnodes_dataのみを受け取る
                element_defs = extract_method(nodes_data)
            else:
                element_defs = extract_method()

            # 結果をキャッシュして返す
            self._parsed_data[element_type] = element_defs
            logger.debug(f"{element_type.value} 定義数: {len(element_defs)}")

            return element_defs

        except Exception as e:
            logger.exception(
                f"ST-Bridge {element_type.value} 解析中に予期しないエラー: {e}"
            )
            return []

    def parse_all_elements(self) -> Dict[str, List[Dict]]:
        """全構造要素の解析を実行

        Returns:
            全要素の解析結果辞書 {element_type: [element_definitions]}
        """
        all_results = {}

        for element_type in ElementType:
            try:
                results = self.parse_element_type(element_type)
                all_results[element_type.value] = results
                logger.info(f"{element_type.value}: {len(results)} 要素を解析")
            except Exception as e:
                logger.error(f"{element_type.value} 解析でエラー: {e}")
                all_results[element_type.value] = []

        return all_results

    def get_element_count(self, element_type: ElementType) -> int:
        """指定要素タイプの要素数を取得"""
        elements = self.parse_element_type(element_type)
        return len(elements)

    def get_total_element_count(self) -> int:
        """全要素の総数を取得"""
        total = 0
        for element_type in ElementType:
            total += self.get_element_count(element_type)
        return total

    def clear_cache(self):
        """パース結果のキャッシュをクリア"""
        self._parsed_data.clear()
        self._is_parsed = False

    def _parse_stories_direct(self) -> List[Dict]:
        """Story要素を直接解析（循環importを回避）"""
        try:
            stb_stories = XMLUtils.find_elements_safe(
                self.xml_parser.root,
                ".//stb:StbStory",
                self.xml_parser.get_namespaces(),
            )
            stories = []
            for story_elem in stb_stories:
                # 基本的なstory属性の取得
                story_data = {
                    "id": story_elem.get("id", ""),
                    "name": story_elem.get("name", ""),
                    "height": float(story_elem.get("height", 0)),
                    "kind": story_elem.get("kind", ""),
                }

                # StbNodeIdListからnode_idsを取得
                node_ids = []
                node_id_list = XMLUtils.find_elements_safe(
                    story_elem,
                    "./stb:StbNodeIdList/stb:StbNodeId",
                    self.xml_parser.get_namespaces(),
                )
                for node_id_elem in node_id_list:
                    node_id = node_id_elem.get("id", "")
                    if node_id:
                        node_ids.append(node_id)

                story_data["node_ids"] = node_ids
                stories.append(story_data)

            logger.debug(
                f"Story直接解析完了: {len(stories)}個の階層, 総ノード数: {sum(len(s['node_ids']) for s in stories)}"
            )
            return stories
        except Exception as e:
            logger.error(f"Story直接解析でエラー: {e}")
            return []

    def _parse_src_sections_direct(self) -> List[Dict]:
        """SRC断面を直接解析（循環importを回避）"""
        try:
            # SRCSectionExtractorを直接インスタンス化して実行
            section_extractor_class = self._get_extractor_class("src_section_extractor.SRCSectionExtractor")
            if not section_extractor_class:
                logger.error("SRCSectionExtractorクラスが見つかりません")
                return []
            
            section_extractor = section_extractor_class(self.xml_parser)
            sections_data = section_extractor.extract_sections()
            
            # 辞書を配列に変換
            sections_list = []
            for section_id, section_info in sections_data.items():
                section_info["id"] = section_id
                sections_list.append(section_info)
            
            logger.debug(f"SRC断面解析完了: {len(sections_list)}個の断面")
            return sections_list
        except Exception as e:
            logger.error(f"SRC断面解析でエラー: {e}")
            return []
