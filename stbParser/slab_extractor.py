"""ST-Bridge スラブ要素抽出クラス"""

from typing import Dict, List, Optional
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger

logger = get_logger(__name__)


class SlabExtractor(BaseExtractor):
    """ST-Bridge スラブメンバーの抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_slabs(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        """スラブメンバー情報を抽出しIFC用辞書リストに変換"""
        config = STBExtractionConfigs.get_slab_config()
        return self.extract_elements(nodes_data, sections_data, config)



    def _extract_single_element(
        self,
        slab_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ) -> Optional[Dict]:
        """単一要素の抽出処理（BaseExtractorから継承）"""
        return self._extract_single_slab(
            slab_elem, nodes_data, sections_data, node_story_map
        )

    def _extract_single_slab(
        self,
        slab_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict,
    ) -> Optional[Dict]:
        slab_id = slab_elem.get("id")
        name = slab_elem.get("name", f"Slab_{slab_id}")
        section_id = slab_elem.get("id_section")
        nodes_text = None
        node_elem = slab_elem.find(
            "stb:StbNodeIdOrder", self.xml_parser.get_namespaces()
        )
        if node_elem is not None:
            nodes_text = node_elem.text
        if not nodes_text or not section_id:
            logger.info("スラブ ID %s の情報が不足しています", slab_id)
            return None

        node_ids = nodes_text.split()
        if not node_ids or section_id not in sections_data:
            logger.info("スラブ ID %s のノードまたは断面が見つかりません", slab_id)
            return None  # オフセット適用済みの節点座標を取得
        corrected_nodes = self._apply_slab_node_offsets(slab_elem, node_ids, nodes_data)

        if not corrected_nodes:
            logger.info("スラブ ID %s のノードが見つかりません", slab_id)
            return None

        # オフセット適用後の座標で中心点と範囲を計算
        center_x = sum(c["x"] for c in corrected_nodes) / len(corrected_nodes)
        center_y = sum(c["y"] for c in corrected_nodes) / len(corrected_nodes)
        center_z = sum(c["z"] for c in corrected_nodes) / len(corrected_nodes)
        width = max(c["x"] for c in corrected_nodes) - min(
            c["x"] for c in corrected_nodes
        )
        depth = max(c["y"] for c in corrected_nodes) - min(
            c["y"] for c in corrected_nodes
        )

        section = sections_data[section_id].copy()
        section.setdefault("width", width)
        section.setdefault("depth", depth)

        slab_def = {
            "name": name,
            "tag": f"SLB_{slab_id}",
            "center_point": {"x": center_x, "y": center_y, "z": center_z},
            "corner_nodes": corrected_nodes,  # オフセット適用済みの節点座標（新規）
            "node_ids": node_ids,  # Story関連付け用（すべてのノード）
            "primary_node_id": node_ids[0],  # Story関連付けの基準（最初のノード）
            "section": section,
            "stb_original_id": slab_id,
            "stb_guid": slab_elem.get("guid"),
            "stb_section_name": section.get("stb_name", "Unknown"),
        }

        # 階層情報を設定（最初のノードのみを使用）
        floor_attribute = slab_elem.get("floor")
        if floor_attribute:
            slab_def["floor"] = floor_attribute
            logger.debug(
                "スラブ ID %s に階層情報を設定: floor='%s'", slab_id, floor_attribute
            )
        elif node_story_map is not None:
            # 最初のノードから階層を特定
            story_name = node_story_map.get(node_ids[0])  # 最初のノードの階層を取得
            if story_name:
                slab_def["floor"] = story_name
                logger.debug(
                    "スラブ ID %s にノードから特定した階層情報を設定: floor='%s'",
                    slab_id,
                    story_name,
                )
            else:
                # ノードが階層に紐づいていない場合、GLレベルに割り当て
                logger.warning(
                    "スラブ ID %s の階層情報を特定できませんでした: primary_node=%s - GLレベルに割り当てます",
                    slab_id,
                    node_ids[0] if node_ids else "None",
                )
                slab_def["floor"] = "GL"

        return slab_def

    def _apply_slab_node_offsets(
        self, slab_elem, node_ids: List[str], nodes_data: Dict[str, Dict]
    ) -> List[Dict]:
        """スラブの各ノードにオフセットを適用

        Args:
            slab_elem: スラブのXML要素
            node_ids: ノードIDリスト
            nodes_data: ノード情報辞書

        Returns:
            オフセット適用済みの節点座標リスト
        """
        namespaces = self.xml_parser.get_namespaces()

        # StbSlabOffsetListを取得
        offset_list_elem = slab_elem.find("stb:StbSlabOffsetList", namespaces)
        if offset_list_elem is None:
            # オフセット情報がない場合は元のノード座標をそのまま使用
            logger.debug(
                "スラブ ID %s にオフセット情報がありません", slab_elem.get("id")
            )
            return [
                nodes_data[node_id].copy()
                for node_id in node_ids
                if node_id in nodes_data
            ]

        # 各ノードのオフセット情報を辞書化
        offset_dict = {}
        for offset_elem in offset_list_elem.findall("stb:StbSlabOffset", namespaces):
            node_id = offset_elem.get("id_node")
            offset_dict[node_id] = {
                "x": float(offset_elem.get("offset_X", 0)),
                "y": float(offset_elem.get("offset_Y", 0)),
                "z": float(offset_elem.get("offset_Z", 0)),
            }

        logger.debug(
            "スラブ ID %s のオフセット情報: %s",
            slab_elem.get("id"),
            {k: f"({v['x']}, {v['y']}, {v['z']})" for k, v in offset_dict.items()},
        )

        # 各ノードにオフセットを適用
        corrected_nodes = []
        for node_id in node_ids:
            if node_id not in nodes_data:
                logger.warning("ノード ID %s が見つかりません", node_id)
                continue

            original_node = nodes_data[node_id]
            offset = offset_dict.get(node_id, {"x": 0, "y": 0, "z": 0})

            corrected_node = {
                "x": original_node["x"] + offset["x"],
                "y": original_node["y"] + offset["y"],
                "z": original_node["z"] + offset["z"],
            }
            corrected_nodes.append(corrected_node)

            if any(offset.values()):  # オフセットが0でない場合のみログ出力
                logger.debug(
                    "ノード ID %s: 元座標(%s, %s, %s) + オフセット(%s, %s, %s) = 補正後(%s, %s, %s)",
                    node_id,
                    original_node["x"],
                    original_node["y"],
                    original_node["z"],
                    offset["x"],
                    offset["y"],
                    offset["z"],
                    corrected_node["x"],
                    corrected_node["y"],
                    corrected_node["z"],
                )

        return corrected_nodes
