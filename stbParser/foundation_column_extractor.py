# foundation_column_extractor.py
import math
from typing import Dict, List, Tuple
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger


logger = get_logger(__name__)


class FoundationColumnExtractor(BaseExtractor):
    """ST-Bridge基礎柱メンバー情報の抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_foundation_columns(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        """ST-Bridgeから基礎柱メンバー情報を抽出してIFC用辞書リストに変換

        Args:
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書

        Returns:
            基礎柱定義リスト（各要素は辞書形式）
        """
        config = STBExtractionConfigs.get_foundation_column_config()
        return self.extract_elements(nodes_data, sections_data, config)



    def _extract_single_element(
        self,
        foundation_column_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ):
        """単一要素の抽出処理（BaseExtractorから継承）"""
        return self._extract_single_foundation_column(
            foundation_column_elem, nodes_data, sections_data, node_story_map
        )

    def _extract_single_foundation_column(
        self,
        foundation_column_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
    ) -> Dict:
        """単一基礎柱要素の情報を抽出

        Args:
            foundation_column_elem: 基礎柱要素
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書

        Returns:
            基礎柱定義辞書、またはNone
        """
        try:
            # 基礎柱の基本属性を取得
            foundation_column_id = foundation_column_elem.get("id")
            foundation_column_guid = foundation_column_elem.get("guid", "")
            foundation_column_name = foundation_column_elem.get(
                "name", f"FoundationColumn_{foundation_column_id}"
            )

            # ノード情報の取得
            id_node = foundation_column_elem.get("id_node")
            if not id_node or id_node not in nodes_data:
                logger.warning(
                    "基礎柱 %s: ノードID %s が見つかりません",
                    foundation_column_id,
                    id_node,
                )
                return None

            node_info = nodes_data[id_node]

            # 構造種別（RC固定）
            kind_structure = foundation_column_elem.get("kind_structure", "RC")
            if kind_structure != "RC":
                logger.warning(
                    "基礎柱 %s: kind_structure が RC ではありません: %s",
                    foundation_column_id,
                    kind_structure,
                )

            # 断面情報の取得（FDセクション）
            id_section_fd = foundation_column_elem.get("id_section_FD")
            fd_section_info = None
            length_fd = 0

            # FD部分が存在する場合の処理
            if (
                id_section_fd
                and id_section_fd != "0"
                and id_section_fd in sections_data
            ):
                fd_section_info = sections_data[id_section_fd]
                length_fd = float(foundation_column_elem.get("length_FD", 0))
            elif id_section_fd == "0":
                logger.info("基礎柱 %s: FD断面は0（無し）です", foundation_column_id)
            else:
                logger.warning(
                    "基礎柱 %s: FD断面ID %s が見つかりません",
                    foundation_column_id,
                    id_section_fd,
                )

            # WR断面情報の確認
            id_section_wr = foundation_column_elem.get("id_section_WR")

            # FD断面もWR断面も無い場合はスキップ
            if (not fd_section_info) and (
                not id_section_wr or id_section_wr not in sections_data
            ):
                logger.warning(
                    "基礎柱 %s: FD断面とWR断面の両方が無効です",
                    foundation_column_id,
                )
                return None

            # 長さ情報
            if length_fd <= 0 and fd_section_info:
                logger.warning(
                    "基礎柱 %s: length_FD が無効です: %f",
                    foundation_column_id,
                    length_fd,
                )

            # オフセット情報（オプション）
            offset_fd_x = float(foundation_column_elem.get("offset_FD_X", 0))
            offset_fd_y = float(foundation_column_elem.get("offset_FD_Y", 0))

            # 厚さ追加情報（オプション）
            thickness_add_fd_start = float(
                foundation_column_elem.get("thickness_add_FD_start", 0)
            )
            thickness_add_fd_end = float(
                foundation_column_elem.get("thickness_add_FD_end", 0)
            )

            # WRセクション情報（オプション）
            id_section_wr = foundation_column_elem.get("id_section_WR")
            wr_section_info = None
            length_wr = 0
            offset_wr_x = 0
            offset_wr_y = 0

            if id_section_wr and id_section_wr in sections_data:
                wr_section_info = sections_data[id_section_wr]
                length_wr = float(foundation_column_elem.get("length_WR", 0))
                offset_wr_x = float(foundation_column_elem.get("offset_WR_X", 0))
                offset_wr_y = float(foundation_column_elem.get("offset_WR_Y", 0))

            # 座標計算
            x = node_info["x"] + offset_fd_x
            y = node_info["y"] + offset_fd_y
            z = node_info["z"]

            # 主要断面の決定（WR部分が存在する場合はWR、そうでなければFD）
            primary_section_info = (
                wr_section_info if wr_section_info else fd_section_info
            )
            primary_section_id = id_section_wr if wr_section_info else id_section_fd

            # 基礎柱定義辞書の構築
            foundation_column_def = {
                "id": foundation_column_id,
                "guid": foundation_column_guid,
                "name": foundation_column_name,
                "type": "FoundationColumn",
                "kind_structure": kind_structure,
                # 位置情報
                "x": x,
                "y": y,
                "z": z,
                # ノード情報
                "id_node": id_node,
                "node_id": id_node,  # Story関連付け用
                "node_info": node_info,
                # FD（Foundation）部分
                "fd_section": {
                    "id_section": id_section_fd,
                    "section_info": fd_section_info,
                    "length": length_fd,
                    "offset_x": offset_fd_x,
                    "offset_y": offset_fd_y,
                    "thickness_add_start": thickness_add_fd_start,
                    "thickness_add_end": thickness_add_fd_end,
                },
                # 断面寸法（主要断面から）
                "width": (
                    primary_section_info.get("width_x", 0)
                    if primary_section_info
                    else 0
                ),
                "height": (
                    primary_section_info.get("width_y", 0)
                    if primary_section_info
                    else 0
                ),  # RC柱の場合 width_y が高さ
                "depth": length_wr if wr_section_info else length_fd,
                # IFC生成用の主要情報
                "id_section": primary_section_id,
                "section_info": primary_section_info,
                # STB要素情報
                "stb_original_id": foundation_column_id,
                "stb_guid": foundation_column_guid,
                "stb_section_name": (
                    primary_section_info.get("stb_name", "Unknown")
                    if primary_section_info
                    else "Unknown"
                ),
            }

            # WR（Wall）部分がある場合
            if wr_section_info:
                foundation_column_def["wr_section"] = {
                    "id_section": id_section_wr,
                    "section_info": wr_section_info,
                    "length": length_wr,
                    "offset_x": offset_wr_x,
                    "offset_y": offset_wr_y,
                }

            # 階層情報を設定（基礎柱は通常最下層）
            floor_attribute = foundation_column_elem.get("floor")
            if floor_attribute:
                foundation_column_def["floor"] = floor_attribute
                logger.debug(
                    "基礎柱 ID %s に階層情報を設定: floor='%s'", foundation_column_id, floor_attribute
                )
            elif node_story_map is not None:
                # ノードから階層を特定
                story_name = node_story_map.get(id_node)  # ノードの階層を取得
                if story_name:
                    foundation_column_def["floor"] = story_name
                    logger.debug(
                        "基礎柱 ID %s にノードから特定した階層情報を設定: floor='%s'",
                        foundation_column_id,
                        story_name,
                    )
                else:
                    logger.warning(
                        "基礎柱 ID %s の階層情報を特定できませんでした: node=%s",
                        foundation_column_id,
                        id_node,
                    )

            logger.debug("基礎柱 %s の抽出完了", foundation_column_id)
            return foundation_column_def

        except Exception as e:
            logger.error(
                "基礎柱 %s の抽出中にエラーが発生しました: %s",
                foundation_column_elem.get("id", "unknown"),
                str(e),
            )
            logger.error("エラー詳細", exc_info=True)
            return None
