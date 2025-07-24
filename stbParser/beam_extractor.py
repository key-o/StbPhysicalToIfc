# beam_extractor.py
import math
import uuid
from typing import Dict, List, Tuple, Optional
from .xml_parser import STBXMLParser
from .base_extractor import BaseExtractor, STBExtractionConfigs
from utils.logger import get_logger


logger = get_logger(__name__)


class BeamExtractor(BaseExtractor):
    """ST-Bridge梁メンバー情報の抽出を担当するクラス"""
    
    def __init__(self, xml_parser: STBXMLParser):
        super().__init__(xml_parser)

    def extract_beams(
        self, nodes_data: Dict[str, Dict], sections_data: Dict[str, Dict]
    ) -> List[Dict]:
        """ST-Bridgeから梁メンバー情報を抽出してIFC用辞書リストに変換

        Args:
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書

        Returns:
            梁定義リスト（各要素は辞書形式）
        """
        config = STBExtractionConfigs.get_beam_config()
        return self.extract_elements(nodes_data, sections_data, config)



    def _extract_single_element(
        self,
        beam_elem,
        nodes_data: Dict[str, Dict],
        sections_data: Dict[str, Dict],
        node_story_map: Dict[str, str],
        element_type: str
    ):
        """単一要素の抽出処理（BaseExtractorから継承）"""
        # 梁の場合は複数の定義を返す可能性があるため（ハンチ付き梁）、
        # リストを直接返す。ベースクラスが適切に処理する。
        return self._extract_single_beam(
            beam_elem, nodes_data, sections_data, element_type, node_story_map
        )

    def _extract_single_beam(
        self,
        beam_elem,
        nodes_data: Dict,
        sections_data: Dict,
        beam_type: str = "StbGirder",
        node_story_map: Optional[Dict[str, str]] = None,
    ) -> List[Dict]:
        """単一の梁要素からIFC用辞書を作成（ハンチ対応）

        Args:
            beam_elem: 梁のXML要素（StbGirderまたはStbBeam）
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書
            beam_type: 梁要素のタイプ（"StbGirder"または"StbBeam"）
            node_story_map: ノードIDと階層名のマッピング

        Returns:
            梁定義辞書のリスト（ハンチの場合は複数）
        """
        beam_id = beam_elem.get("id")
        beam_name = beam_elem.get("name", f"{beam_type}_{beam_id}")
        id_node_start = beam_elem.get("id_node_start")
        id_node_end = beam_elem.get("id_node_end")
        id_section = beam_elem.get("id_section")
        kind_structure = beam_elem.get("kind_structure")

        # 回転角度の取得
        rotate_degrees = float(beam_elem.get("rotate", 0))
        rotate_radians = self._degrees_to_radians(rotate_degrees)  # ハンチ長さの取得
        haunch_start = beam_elem.get("haunch_start")
        haunch_end = beam_elem.get("haunch_end")

        # 必要なデータの存在確認
        if not self._validate_beam_data(
            beam_id, id_node_start, id_node_end, id_section, nodes_data, sections_data
        ):
            return []

        # section_info取得: id_sectionで見つからない場合はshape_nameで再検索
        try:
            section_info = sections_data[id_section]
        except KeyError:  # shape名で再検索
            steel_figure = beam_elem.find(
                ".//stb:StbSecSteelFigureBeam_S/stb:StbSecSteelBeam_S_Straight",
                self.xml_parser.get_namespaces(),
            )
            shape_name = steel_figure.get("shape") if steel_figure is not None else None
            if shape_name and shape_name in sections_data:
                section_info = sections_data[shape_name]
            else:
                logger.warning(
                    "%s ID %s の完全なデータが見つかりません (section %s, shape %s)",
                    beam_type,
                    beam_id,
                    id_section,
                    shape_name,
                )
                return []  # ハンチ付き梁かどうかを判定 (FiveTypes も含む)
        if section_info.get("section_type") in {"HAUNCH", "HAUNCH_FIVE"}:
            return self._create_haunch_beam_definitions(
                beam_elem,
                nodes_data,
                section_info,
                beam_id,
                beam_name,
                kind_structure,
                node_story_map,
            )
        else:
            # 通常の梁
            beam_def = self._create_normal_beam_definition(
                beam_elem,
                nodes_data,
                section_info,
                beam_id,
                beam_name,
                kind_structure,
                node_story_map,
            )
            return [beam_def] if beam_def else []

    def _create_haunch_beam_definitions(
        self,
        girder_elem,
        nodes_data: Dict,
        section_info: Dict,
        girder_id: str,
        girder_name: str,
        kind_structure: str,
        node_story_map: Optional[Dict[str, str]] = None,
    ) -> List[Dict]:
        """ハンチ付き梁の定義を作成（3つの梁に分割）"""
        haunch_start = float(girder_elem.get("haunch_start", 0))
        haunch_end = float(girder_elem.get("haunch_end", 0))

        # オフセットを適用した座標を取得
        start_node, end_node = self._apply_node_offsets(girder_elem, nodes_data)
        haunch_sections = section_info["haunch_sections"]

        # 梁の全長と方向ベクトルを計算
        total_length, direction_vector = self._calculate_beam_length_and_direction(
            start_node, end_node
        )

        if total_length <= haunch_start + haunch_end:
            logger.warning(
                "全長 %s がハンチ長さの合計 %s より短すぎます",
                total_length,
                haunch_start + haunch_end,
            )
            return []

        # 各セグメントの長さを計算
        center_length = total_length - haunch_start - haunch_end

        # 各セグメントの開始・終了点を計算
        segments = self._calculate_segment_points(
            start_node, direction_vector, haunch_start, center_length, haunch_end
        )

        beam_definitions = []

        # 各セグメントの梁定義を作成
        for i, (segment_name, start_point, end_point) in enumerate(segments):
            # セグメント断面が無い場合、CENTERはhaunch長さが0の方の断面を流用
            if segment_name not in haunch_sections:
                # CENTER区間の断面が無い場合の流用ロジック
                if segment_name == "CENTER":
                    # haunch_startが0ならSTART断面、haunch_endが0ならEND断面を流用
                    if haunch_start == 0 and "START" in haunch_sections:
                        section = haunch_sections["START"]
                    elif haunch_end == 0 and "END" in haunch_sections:
                        section = haunch_sections["END"]
                    else:
                        logger.warning(
                            "セグメント %s の断面が見つかりません", segment_name
                        )
                        continue
                else:
                    logger.warning("セグメント %s の断面が見つかりません", segment_name)
                    continue
            else:
                section = haunch_sections[segment_name]  # ノードIDを取得
            id_node_start = girder_elem.get("id_node_start")
            id_node_end = girder_elem.get("id_node_end")

            # 各セグメントに一意のGUIDを生成
            original_guid = girder_elem.get("guid", "")
            # セグメントタイプとインデックスを使用してユニークなGUIDを生成
            segment_guid = str(
                uuid.uuid5(
                    uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
                    f"{original_guid}_{segment_name}_{i}",
                )
            )

            beam_def = {
                "name": f"{girder_name}_{segment_name}",
                "tag": f"STB_G_{girder_id}_{segment_name}",
                "start_point": start_point,
                "end_point": end_point,
                "start_node_id": id_node_start,  # ノードIDを追加
                "end_node_id": id_node_end,  # ノードIDを追加
                "section": section,
                "stb_original_id": girder_id,
                "stb_guid": segment_guid,  # ユニークなGUIDを使用
                "stb_original_guid": original_guid,  # 元のGUIDも保持
                "stb_section_name": section.get("stb_name", "Unknown"),
                "stb_structure_type": kind_structure,
                "stb_segment_type": segment_name,  # START, CENTER, END
                "stb_segment_index": i,
            }

            # 階層情報を設定
            floor_attribute = girder_elem.get("floor")
            if floor_attribute:
                beam_def["floor"] = floor_attribute
            elif node_story_map is not None:
                # ノードから階層を特定
                story_name = node_story_map.get(id_node_start)  # 開始ノードの階層を取得
                if story_name:
                    beam_def["floor"] = story_name
                else:
                    logger.warning(
                        "ハンチ梁セグメント %s の階層情報を特定できませんでした: girder_id=%s, node_start=%s",
                        segment_name,
                        girder_id,
                        id_node_start,
                    )
            else:
                logger.warning(
                    "ハンチ梁セグメント %s の階層マッピングが利用できません: girder_id=%s",
                    segment_name,
                    girder_id,
                )

            beam_definitions.append(beam_def)
            logger.info(
                "梁セグメント %s を作成 (Girder ID %s)",
                segment_name,
                girder_id,
            )

        return beam_definitions

    def _create_normal_beam_definition(
        self,
        girder_elem,
        nodes_data: Dict,
        section_info: Dict,
        girder_id: str,
        girder_name: str,
        kind_structure: str,
        node_story_map: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """通常の梁定義を作成"""
        # ノードIDを取得
        id_node_start = girder_elem.get("id_node_start")
        id_node_end = girder_elem.get("id_node_end")

        # オフセットを適用した座標を取得
        start_node, end_node = self._apply_node_offsets(girder_elem, nodes_data)

        beam_def = {
            "name": girder_name,
            "tag": f"STB_G_{girder_id}",
            "start_point": start_node,
            "end_point": end_node,
            "start_node_id": id_node_start,  # ノードIDを追加
            "end_node_id": id_node_end,  # ノードIDを追加
            "stb_original_id": girder_id,
            "stb_guid": girder_elem.get("guid"),
            "stb_section_name": section_info.get("stb_name", "Unknown"),
            "stb_structure_type": kind_structure,
        }

        # 階層情報を設定
        floor_attribute = girder_elem.get("floor")
        if floor_attribute:
            beam_def["floor"] = floor_attribute
            logger.debug(
                "梁 ID %s に階層情報を設定: floor='%s'", girder_id, floor_attribute
            )
        elif node_story_map is not None:
            # ノードから階層を特定
            story_name = node_story_map.get(id_node_start)  # 開始ノードの階層を取得
            if story_name:
                beam_def["floor"] = story_name
                logger.debug(
                    "梁 ID %s にノードから特定した階層情報を設定: floor='%s'",
                    girder_id,
                    story_name,
                )
            else:
                logger.warning(
                    "梁 ID %s の階層情報を特定できませんでした: node_start=%s",
                    girder_id,
                    id_node_start,
                )

        if "start_section" in section_info and "end_section" in section_info:
            beam_def["section_start"] = section_info["start_section"]
            beam_def["section_end"] = section_info["end_section"]
        else:
            beam_def["section"] = section_info

        return beam_def

    def _apply_node_offsets(self, girder_elem, nodes_data: Dict) -> Tuple[Dict, Dict]:
        """ノード座標にオフセットを適用して補正された座標を返す

        Args:
            girder_elem: 梁のXML要素
            nodes_data: ノード情報辞書

        Returns:
            補正された開始ノードと終了ノードの座標
        """
        from common.extractor_utils import NodeOffsetUtils

        return NodeOffsetUtils.apply_node_offsets(girder_elem, nodes_data)

    def _calculate_beam_length_and_direction(
        self, start_node: Dict, end_node: Dict
    ) -> Tuple[float, Dict]:
        """梁の長さと方向ベクトルを計算"""
        dx = end_node["x"] - start_node["x"]
        dy = end_node["y"] - start_node["y"]
        dz = end_node["z"] - start_node["z"]

        length = math.sqrt(dx * dx + dy * dy + dz * dz)

        if length == 0:
            return 0, {"x": 1, "y": 0, "z": 0}

        # 正規化された方向ベクトル
        direction = {"x": dx / length, "y": dy / length, "z": dz / length}

        return length, direction

    def _degrees_to_radians(self, degrees: float) -> float:
        """度をラジアンに変換

        Args:
            degrees: 角度（度）

        Returns:
            角度（ラジアン）
        """
        from common.extractor_utils import AngleUtils

        return AngleUtils.degrees_to_radians(degrees)

    def _calculate_segment_points(
        self,
        start_node: Dict,
        direction: Dict,
        haunch_start: float,
        center_length: float,
        haunch_end: float,
    ) -> List[Tuple[str, Dict, Dict]]:
        """各セグメントの開始・終了点を計算"""
        segments = []
        current_distance = 0

        # START セグメント
        if haunch_start > 0:
            start_point = start_node.copy()
            end_point = {
                "x": start_node["x"] + direction["x"] * haunch_start,
                "y": start_node["y"] + direction["y"] * haunch_start,
                "z": start_node["z"] + direction["z"] * haunch_start,
            }
            segments.append(("START", start_point, end_point))
            current_distance += haunch_start

        # CENTER セグメント
        if center_length > 0:
            start_point = {
                "x": start_node["x"] + direction["x"] * current_distance,
                "y": start_node["y"] + direction["y"] * current_distance,
                "z": start_node["z"] + direction["z"] * current_distance,
            }
            current_distance += center_length
            end_point = {
                "x": start_node["x"] + direction["x"] * current_distance,
                "y": start_node["y"] + direction["y"] * current_distance,
                "z": start_node["z"] + direction["z"] * current_distance,
            }
            segments.append(("CENTER", start_point, end_point))

        # END セグメント
        if haunch_end > 0:
            start_point = {
                "x": start_node["x"] + direction["x"] * current_distance,
                "y": start_node["y"] + direction["y"] * current_distance,
                "z": start_node["z"] + direction["z"] * current_distance,
            }
            end_point = {
                "x": start_node["x"] + direction["x"] * (current_distance + haunch_end),
                "y": start_node["y"] + direction["y"] * (current_distance + haunch_end),
                "z": start_node["z"] + direction["z"] * (current_distance + haunch_end),
            }
            segments.append(("END", start_point, end_point))

        return segments

    def _validate_beam_data(
        self,
        girder_id: str,
        id_node_start: str,
        id_node_end: str,
        id_section: str,
        nodes_data: Dict,
        sections_data: Dict,
    ) -> bool:
        """梁データの妥当性を確認

        Args:
            girder_id: 梁ID
            id_node_start: 開始ノードID
            id_node_end: 終了ノードID
            id_section: 断面ID
            nodes_data: ノード情報辞書
            sections_data: 断面情報辞書

        Returns:
            データが揃っている場合True、不足している場合False
        """
        from common.extractor_utils import ElementValidator

        return ElementValidator.validate_element_data(
            girder_id,
            "Girder",
            [id_node_start, id_node_end],
            [id_section],
            nodes_data,
            sections_data,
        )
