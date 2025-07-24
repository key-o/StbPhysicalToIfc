"""ST-Bridge 通芯メンバーの抽出を担当するクラス"""

from typing import List, Dict, Optional
from .xml_parser import STBXMLParser
from utils.logger import get_logger

logger = get_logger(__name__)


class AxesExtractor:
    """ST-Bridge 通芯メンバーの抽出を担当するクラス"""

    def __init__(self, xml_parser: STBXMLParser):
        self.xml_parser = xml_parser

    def extract_axes(self, nodes_data: Dict[str, Dict]) -> List[Dict]:
        """通芯情報を抽出しIFC用辞書リストに変換"""
        axes_list: List[Dict] = []
        
        stb_model = self.xml_parser.find_element(".//stb:StbModel")
        if stb_model is None:
            logger.warning("StbModel 要素が見つかりません")
            return axes_list

        namespaces = self.xml_parser.get_namespaces()
        axes_elem = stb_model.find(".//stb:StbAxes", namespaces)
        if axes_elem is None:
            logger.info("StbAxes 要素が見つかりません")
            return axes_list

        # StbParallelAxes要素を処理
        for parallel_axes_elem in axes_elem.findall("stb:StbParallelAxes", namespaces):
            axes_group = self._extract_parallel_axes_group(parallel_axes_elem, nodes_data)
            if axes_group:
                axes_list.append(axes_group)

        logger.info("通芯グループ数: %d", len(axes_list))
        return axes_list

    def _extract_parallel_axes_group(
        self, parallel_axes_elem, nodes_data: Dict[str, Dict]
    ) -> Optional[Dict]:
        """並行通芯グループを抽出"""
        group_name = parallel_axes_elem.get("group_name", "Unknown")
        origin_x = float(parallel_axes_elem.get("X", 0))
        origin_y = float(parallel_axes_elem.get("Y", 0))
        angle = float(parallel_axes_elem.get("angle", 0))

        namespaces = self.xml_parser.get_namespaces()
        axes_in_group = []

        for axis_elem in parallel_axes_elem.findall("stb:StbParallelAxis", namespaces):
            axis_def = self._extract_single_axis(axis_elem, nodes_data, origin_x, origin_y, angle)
            if axis_def:
                axes_in_group.append(axis_def)

        if not axes_in_group:
            logger.warning("通芯グループ %s に軸が見つかりません", group_name)
            return None

        return {
            "group_name": group_name,
            "origin_x": origin_x,
            "origin_y": origin_y,
            "angle": angle,
            "axes": axes_in_group,
        }

    def _extract_single_axis(
        self, axis_elem, nodes_data: Dict[str, Dict], origin_x: float, origin_y: float, angle: float
    ) -> Optional[Dict]:
        """個別の通芯を抽出"""
        axis_id = axis_elem.get("id")
        axis_name = axis_elem.get("name", f"Axis_{axis_id}")
        distance = float(axis_elem.get("distance", 0))

        # 通芯上の節点IDリストを取得
        namespaces = self.xml_parser.get_namespaces()
        node_list_elem = axis_elem.find("stb:StbNodeIdList", namespaces)
        
        if node_list_elem is None:
            logger.warning("通芯 %s にノードリストが見つかりません", axis_name)
            return None

        node_ids = []
        for node_id_elem in node_list_elem.findall("stb:StbNodeId", namespaces):
            node_id = node_id_elem.get("id")
            if node_id:
                node_ids.append(node_id)

        if not node_ids:
            logger.warning("通芯 %s にノードが見つかりません", axis_name)
            return None

        # 通芯上の節点座標を取得
        axis_nodes = []
        for node_id in node_ids:
            if node_id in nodes_data:
                node_coord = nodes_data[node_id]
                axis_nodes.append({
                    "node_id": node_id,
                    "x": node_coord["x"],
                    "y": node_coord["y"],
                    "z": node_coord["z"]
                })

        if len(axis_nodes) < 2:
            logger.warning("通芯 %s の節点が不足しています（最低2点必要）", axis_name)
            return None

        # 通芯の開始点と終了点を計算
        start_point, end_point = self._calculate_axis_line(axis_nodes, origin_x, origin_y, angle, distance)

        logger.debug(
            "通芯抽出: ID=%s, 名前=%s, distance=%s, 節点数=%d",
            axis_id, axis_name, distance, len(axis_nodes)
        )

        return {
            "id": axis_id,
            "name": axis_name,
            "distance": distance,
            "start_point": start_point,
            "end_point": end_point,
            "axis_nodes": axis_nodes,
            "stb_guid": axis_elem.get("guid"),
        }

    def _calculate_axis_line(
        self, 
        axis_nodes: List[Dict], 
        origin_x: float, 
        origin_y: float, 
        angle: float, 
        distance: float
    ) -> tuple:
        """通芯の開始点と終了点を計算"""
        import math
        
        # 節点のZ座標の範囲を取得
        z_coords = [node["z"] for node in axis_nodes]
        min_z = min(z_coords)
        max_z = max(z_coords)

        # 角度をラジアンに変換
        angle_rad = math.radians(angle)
        
        # 通芯の方向ベクトル（垂直方向）
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        
        # 距離分だけオフセットした位置を計算
        axis_x = origin_x + distance * (-sin_angle)  # 垂直方向へのオフセット
        axis_y = origin_y + distance * cos_angle

        # 通芯の範囲を節点のXY座標から推定
        if abs(cos_angle) > abs(sin_angle):  # 主にX方向の通芯
            x_coords = [node["x"] for node in axis_nodes]
            start_x = min(x_coords)
            end_x = max(x_coords)
            
            start_point = {"x": start_x, "y": axis_y, "z": min_z}
            end_point = {"x": end_x, "y": axis_y, "z": max_z}
        else:  # 主にY方向の通芯
            y_coords = [node["y"] for node in axis_nodes]
            start_y = min(y_coords)
            end_y = max(y_coords)
            
            start_point = {"x": axis_x, "y": start_y, "z": min_z}
            end_point = {"x": axis_x, "y": end_y, "z": max_z}

        return start_point, end_point