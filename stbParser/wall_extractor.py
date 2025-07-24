"""ST-Bridge 壁要素抽出クラス"""

from typing import Dict, List, Optional
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger

logger = get_logger(__name__)


class WallExtractor(BaseExtractor):
    """ST-Bridge 壁メンバーの抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_walls(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        """壁メンバー情報を抽出しIFC用辞書リストに変換"""
        config = STBExtractionConfigs.get_wall_config()
        return self.extract_elements(nodes_data, sections_data, config)



    def _extract_single_element(
        self,
        wall_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ) -> Optional[Dict]:
        """単一要素の抽出処理（BaseExtractorから継承）"""
        return self._extract_single_wall(
            wall_elem, nodes_data, sections_data, node_story_map
        )

    def _extract_single_wall(
        self,
        wall_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict,
    ) -> Optional[Dict]:
        wall_id = wall_elem.get("id")
        name = wall_elem.get("name", f"Wall_{wall_id}")
        section_id = wall_elem.get("id_section")
        node_elem = wall_elem.find(
            "stb:StbNodeIdOrder", self.xml_parser.get_namespaces()
        )
        if node_elem is None or not section_id:
            logger.warning("壁 ID %s の情報が不足しています", wall_id)
            return None
        node_ids = node_elem.text.split()
        # オフセット適用済みの節点座標を取得
        corrected_nodes = self._apply_wall_node_offsets(wall_elem, node_ids, nodes_data)

        if len(corrected_nodes) < 4 or section_id not in sections_data:
            logger.warning("壁 ID %s のノードまたは断面が見つかりません", wall_id)
            return None
        # オフセット適用後の座標で計算
        # STBでは通常、底面4点→上面4点の順で定義される
        bottom_nodes = corrected_nodes[:4]  # 最初の4点は底面
        center_x = sum(c["x"] for c in bottom_nodes) / len(bottom_nodes)
        center_y = sum(c["y"] for c in bottom_nodes) / len(bottom_nodes)
        center_z = sum(c["z"] for c in bottom_nodes) / len(bottom_nodes)

        # 壁の方向ベクトルを計算（底面の最長辺）
        # STBでは壁の中心線が定義され、厚さは断面で指定される
        edges = []
        for i in range(len(bottom_nodes)):
            next_i = (i + 1) % len(bottom_nodes)
            edge_x = bottom_nodes[next_i]["x"] - bottom_nodes[i]["x"]
            edge_y = bottom_nodes[next_i]["y"] - bottom_nodes[i]["y"]
            edge_len = (edge_x**2 + edge_y**2) ** 0.5
            if edge_len > 0:  # 長さ0の辺は除外
                edges.append((edge_x, edge_y, edge_len))

        # 最長辺を壁の方向とする
        if edges:
            longest_edge = max(edges, key=lambda x: x[2])
            wall_direction_x = longest_edge[0]
            wall_direction_y = longest_edge[1]
            length = longest_edge[2]
        else:
            # フォールバック：対角線を使用
            diagonal1_x = bottom_nodes[2]["x"] - bottom_nodes[0]["x"]
            diagonal1_y = bottom_nodes[2]["y"] - bottom_nodes[0]["y"]
            diagonal2_x = bottom_nodes[3]["x"] - bottom_nodes[1]["x"]
            diagonal2_y = bottom_nodes[3]["y"] - bottom_nodes[1]["y"]

            diag1_len = (diagonal1_x**2 + diagonal1_y**2) ** 0.5
            diag2_len = (diagonal2_x**2 + diagonal2_y**2) ** 0.5

            if diag1_len > diag2_len:
                wall_direction_x = diagonal1_x
                wall_direction_y = diagonal1_y
                length = diag1_len
            else:
                wall_direction_x = diagonal2_x
                wall_direction_y = diagonal2_y
                length = diag2_len

        wall_direction_z = 0.0  # 壁の方向は水平面のみ考慮

        # 壁の高さを計算（オフセット適用後の座標を使用）
        if len(corrected_nodes) >= 8:  # 8点で定義される場合（底面4点+上面4点）
            height = abs(corrected_nodes[4]["z"] - corrected_nodes[0]["z"])
        elif len(corrected_nodes) >= 6:  # 6点で定義される場合（底面3点+上面3点）
            # 6点の場合：底面3点（0,1,2）+ 上面3点（3,4,5）
            height = abs(corrected_nodes[3]["z"] - corrected_nodes[0]["z"])
        else:  # 4点の場合はZ座標の最大差
            z_coords = [c["z"] for c in corrected_nodes]
            height = max(z_coords) - min(z_coords)

        # 壁の方向ベクトルを正規化（水平方向のみ）
        if length > 0:
            wall_direction_x /= length
            wall_direction_y /= length
            # wall_direction_z は既に 0.0
        else:
            # 長さが0の場合はデフォルトでX方向とする
            wall_direction_x, wall_direction_y, wall_direction_z = 1.0, 0.0, 0.0

        section = sections_data[section_id].copy()
        section.setdefault("length", length)
        section.setdefault("height", height)

        # 開口情報を抽出
        openings = self._extract_wall_openings(wall_elem, corrected_nodes[0])

        wall_def = {
            "name": name,
            "tag": f"WL_{wall_id}",
            "center_point": {"x": center_x, "y": center_y, "z": center_z},
            "wall_direction": {
                "x": wall_direction_x,
                "y": wall_direction_y,
                "z": wall_direction_z,
            },
            "corner_nodes": corrected_nodes,  # オフセット適用済みの壁の4隅（または8点）の節点座標
            "node_ids": node_ids,  # Story関連付け用（すべてのノード）
            "primary_node_id": node_ids[0],  # Story関連付けの基準（最初のノード）
            "section": section,
            "stb_original_id": wall_id,
            "stb_guid": wall_elem.get("guid"),
            "stb_section_name": section.get("stb_name", "Unknown"),
            "openings": openings,  # 開口情報を追加
        }

        # 階層情報を設定（最初のノードのみを使用）
        floor_attribute = wall_elem.get("floor")
        if floor_attribute:
            wall_def["floor"] = floor_attribute
            logger.debug(
                "壁 ID %s に階層情報を設定: floor='%s'", wall_id, floor_attribute
            )
        elif node_story_map is not None:
            # 最初のノードから階層を特定
            story_name = node_story_map.get(node_ids[0])  # 最初のノードの階層を取得
            if story_name:
                wall_def["floor"] = story_name
                logger.debug(
                    "壁 ID %s にノードから特定した階層情報を設定: floor='%s'",
                    wall_id,
                    story_name,
                )
            else:
                logger.warning(
                    "壁 ID %s の階層情報を特定できませんでした: primary_node=%s",
                    wall_id,
                    node_ids[0] if node_ids else "None",
                )

        return wall_def

    def _apply_wall_node_offsets(
        self, wall_elem, node_ids: List[str], nodes_data: Dict[str, Dict]
    ) -> List[Dict]:
        """壁の各ノードにオフセットを適用

        Args:
            wall_elem: 壁のXML要素
            node_ids: ノードIDリスト
            nodes_data: ノード情報辞書

        Returns:
            オフセット適用済みの節点座標リスト
        """
        namespaces = self.xml_parser.get_namespaces()

        # StbWallOffsetListを取得
        offset_list_elem = wall_elem.find("stb:StbWallOffsetList", namespaces)
        if offset_list_elem is None:
            # オフセット情報がない場合は元のノード座標をそのまま使用
            logger.debug("壁 ID %s にオフセット情報がありません", wall_elem.get("id"))
            return [
                nodes_data[node_id].copy()
                for node_id in node_ids
                if node_id in nodes_data
            ]

        # 各ノードのオフセット情報を辞書化
        offset_dict = {}
        for offset_elem in offset_list_elem.findall("stb:StbWallOffset", namespaces):
            node_id = offset_elem.get("id_node")
            offset_dict[node_id] = {
                "x": float(offset_elem.get("offset_X", 0)),
                "y": float(offset_elem.get("offset_Y", 0)),
                "z": float(offset_elem.get("offset_Z", 0)),
            }

        logger.debug(
            "壁 ID %s のオフセット情報: %s",
            wall_elem.get("id"),
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

    def _extract_wall_openings(self, wall_elem, reference_node: Dict) -> List[Dict]:
        """壁の開口情報を抽出

        Args:
            wall_elem: 壁のXML要素
            reference_node: 壁の最初の節点座標（開口位置の基準点）

        Returns:
            開口情報のリスト
        """
        openings = []
        namespaces = self.xml_parser.get_namespaces()

        # StbOpenIdListを取得
        open_id_list = wall_elem.find("stb:StbOpenIdList", namespaces)
        if open_id_list is None:
            return openings

        # 開口IDリストを取得
        open_ids = []
        for open_id_elem in open_id_list.findall("stb:StbOpenId", namespaces):
            open_id = open_id_elem.get("id")
            if open_id:
                open_ids.append(open_id)

        if not open_ids:
            return openings

        # 開口定義を検索
        stb_opens = self.xml_parser.find_element(".//stb:StbOpens")
        if stb_opens is None:
            logger.warning("StbOpens 要素が見つかりません")
            return openings

        for open_elem in stb_opens.findall("stb:StbOpen", namespaces):
            open_id = open_elem.get("id")
            if open_id in open_ids:
                opening = self._parse_opening(open_elem, reference_node)
                if opening:
                    openings.append(opening)

        logger.debug(
            "壁 ID %s に %d 個の開口を検出", wall_elem.get("id"), len(openings)
        )
        return openings

    def _parse_opening(self, open_elem, reference_node: Dict) -> Optional[Dict]:
        """開口要素を解析

        Args:
            open_elem: 開口のXML要素
            reference_node: 基準となる節点座標

        Returns:
            開口情報の辞書
        """
        try:
            open_id = open_elem.get("id")
            guid = open_elem.get("guid")

            # 開口の位置とサイズを取得
            position_x = float(open_elem.get("position_X", 0))
            position_y = float(open_elem.get("position_Y", 0))
            length_x = float(open_elem.get("length_X", 0))
            length_y = float(open_elem.get("length_Y", 0))
            rotate = float(open_elem.get("rotate", 0))

            # 基準節点からの絶対座標を計算
            # STBではposition_Xが壁の長手方向、position_Yが高さ方向のオフセット
            absolute_x = reference_node["x"] + position_x
            absolute_y = reference_node["y"]  # Y座標は変更しない（壁の厚さ方向）
            absolute_z = (
                reference_node["z"] + position_y
            )  # position_Yは高さ方向のオフセット

            return {
                "id": open_id,
                "guid": guid,
                "position": {"x": absolute_x, "y": absolute_y, "z": absolute_z},
                "relative_position": {"x": position_x, "y": position_y},
                "dimensions": {"width": length_x, "height": length_y},
                "rotation": rotate,
            }

        except (ValueError, TypeError) as e:
            logger.warning("開口 ID %s の解析に失敗: %s", open_elem.get("id"), e)
            return None
