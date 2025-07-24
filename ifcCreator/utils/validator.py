"""Validator

v2.2.0 統合バリデータ
全バリデーション機能を統合
"""

from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class Validator:
    """統合バリデータ
    
    v2.2.0: 全バリデーション機能を統一
    """
    
    def __init__(self):
        self.logger = logger
        
    def validate_beam_definition(self, definition: Dict[str, Any]) -> bool:
        """梁定義をバリデート
        
        Args:
            definition: 梁定義辞書
            
        Returns:
            bool: バリデーション結果
            
        Raises:
            ValueError: バリデーションエラー
        """
        if not isinstance(definition, dict):
            raise ValueError("梁定義は辞書である必要があります")
        
        # 必須フィールドのチェック
        required_fields = ['start_point', 'end_point']
        missing_fields = [field for field in required_fields if field not in definition or definition[field] is None]
        if missing_fields:
            raise ValueError(f"梁定義に必須フィールドが不足しています: {', '.join(missing_fields)}")
        
        # 断面情報の検証（通常梁またはテーパー梁）
        section = definition.get('section')
        section_start = definition.get('section_start')
        section_end = definition.get('section_end')
        
        if section:
            # 通常梁の場合
            if not isinstance(section, dict):
                raise ValueError("断面情報は辞書である必要があります")
            if 'section_type' not in section:
                raise ValueError("断面情報に'section_type'が必要です")
        elif section_start and section_end:
            # テーパー梁の場合
            if not isinstance(section_start, dict) or not isinstance(section_end, dict):
                raise ValueError("テーパー梁の断面情報は辞書である必要があります")
            if 'section_type' not in section_start:
                raise ValueError("開始断面情報に'section_type'が必要です")
            if 'section_type' not in section_end:
                raise ValueError("終了断面情報に'section_type'が必要です")
        else:
            raise ValueError("梁定義に断面情報('section'または'section_start'+'section_end')が必要です")
        
        # 座標点の検証
        self._validate_point(definition['start_point'], '開始点')
        self._validate_point(definition['end_point'], '終了点')
            
        # 梁の長さをチェック（0でないことを確認）
        start = definition['start_point']
        end = definition['end_point']
        if self._points_are_identical(start, end):
            raise ValueError("梁の開始点と終了点が同一です")
        
        return True
    
    def validate_column_definition(self, definition: Dict[str, Any]) -> bool:
        """柱定義をバリデート
        
        Args:
            definition: 柱定義辞書
            
        Returns:
            bool: バリデーション結果
            
        Raises:
            ValueError: バリデーションエラー
        """
        if not isinstance(definition, dict):
            raise ValueError("柱定義は辞書である必要があります")
        
        # 必須フィールドのチェック
        required_fields = ['bottom_point', 'top_point']
        missing_fields = [field for field in required_fields if field not in definition or definition[field] is None]
        if missing_fields:
            raise ValueError(f"柱定義に必須フィールドが不足しています: {', '.join(missing_fields)}")
        
        # 断面情報の検証（通常柱またはテーパー柱）
        section = definition.get('section')
        sec_bottom = definition.get('sec_bottom')
        sec_top = definition.get('sec_top')
        
        if section:
            # 通常柱の場合 - sectionは辞書またはStructuralSectionオブジェクト
            if not (isinstance(section, dict) or hasattr(section, 'section_type')):
                raise ValueError("断面情報は辞書またはStructuralSectionオブジェクトである必要があります")
        elif sec_bottom:
            # テーパー柱の場合 - sec_bottomは辞書またはStructuralSectionオブジェクト
            if not (isinstance(sec_bottom, dict) or hasattr(sec_bottom, 'section_type')):
                raise ValueError("下端断面情報は辞書またはStructuralSectionオブジェクトである必要があります")
            # sec_topは任意（None の場合は sec_bottom と同じとして扱う）
            if sec_top and not (isinstance(sec_top, dict) or hasattr(sec_top, 'section_type')):
                raise ValueError("上端断面情報は辞書またはStructuralSectionオブジェクトである必要があります")
        else:
            raise ValueError("柱定義に断面情報が不足しています: section, sec_bottom, sec_top のいずれかが必要")
        
        # 座標点の検証
        self._validate_point(definition['bottom_point'], '下端点')
        self._validate_point(definition['top_point'], '上端点')
        
        # 断面情報の検証（辞書またはStructuralSectionオブジェクト対応）
        section = definition['section']
        from ..utils.structural_section import StructuralSection
        
        if isinstance(section, StructuralSection):
            # StructuralSectionオブジェクトの場合
            if not section.section_type:
                raise ValueError("断面情報にsection_typeが必要です")
        elif isinstance(section, dict):
            # 辞書の場合（従来の処理）
            if 'section_type' not in section:
                raise ValueError("断面情報に'section_type'が必要です")
        else:
            raise ValueError("断面情報は辞書またはStructuralSectionオブジェクトである必要があります")
            
        # 柱の高さをチェック（0でないことを確認）
        bottom = definition['bottom_point']
        top = definition['top_point']
        if self._points_are_identical(bottom, top):
            raise ValueError("柱の下端点と上端点が同一です")
            
        # 柱の高さが適切かチェック（上端が下端より上にあるか）
        from common.geometry import Point3D
        
        def get_z_coord(point):
            if isinstance(point, Point3D):
                return point.z
            elif isinstance(point, dict):
                return point.get('z', 0)
            else:
                return 0
        
        top_z = get_z_coord(top)
        bottom_z = get_z_coord(bottom)
        
        if top_z <= bottom_z:
            raise ValueError("柱の上端点が下端点より下にあります")
        
        return True
    
    def validate_slab_definition(self, definition: Dict[str, Any]) -> bool:
        """スラブ定義をバリデート
        
        Args:
            definition: スラブ定義辞書
            
        Returns:
            bool: バリデーション結果
            
        Raises:
            ValueError: バリデーションエラー
        """
        if not isinstance(definition, dict):
            raise ValueError("スラブ定義は辞書である必要があります")
        
        # 必須フィールドのチェック
        required_fields = ['corner_nodes', 'section']
        missing_fields = [field for field in required_fields if field not in definition or definition[field] is None]
        if missing_fields:
            raise ValueError(f"スラブ定義に必須フィールドが不足しています: {', '.join(missing_fields)}")
        
        # コーナーノードの検証
        corner_nodes = definition['corner_nodes']
        if not isinstance(corner_nodes, list) or len(corner_nodes) < 3:
            raise ValueError("スラブには最低3つのコーナーノードが必要です")
        
        # 各コーナーノードの検証
        for i, node in enumerate(corner_nodes):
            self._validate_point(node, f'コーナーノード{i+1}')
        
        # 断面情報の検証
        section = definition['section']
        if not isinstance(section, dict):
            raise ValueError("断面情報は辞書である必要があります")
        
        if 'section_type' not in section:
            raise ValueError("断面情報に'section_type'が必要です")
        
        return True
    
    def validate_wall_definition(self, definition: Dict[str, Any]) -> bool:
        """壁定義をバリデート
        
        Args:
            definition: 壁定義辞書
            
        Returns:
            bool: バリデーション結果
            
        Raises:
            ValueError: バリデーションエラー
        """
        if not isinstance(definition, dict):
            raise ValueError("壁定義は辞書である必要があります")
        
        # 必須フィールドのチェック
        required_fields = ['corner_nodes', 'section']
        missing_fields = [field for field in required_fields if field not in definition or definition[field] is None]
        if missing_fields:
            raise ValueError(f"壁定義に必須フィールドが不足しています: {', '.join(missing_fields)}")
        
        # コーナーノードの検証
        corner_nodes = definition['corner_nodes']
        if not isinstance(corner_nodes, list) or len(corner_nodes) < 2:
            raise ValueError("壁には最低2つのコーナーノードが必要です")
        
        # 各コーナーノードの検証
        for i, node in enumerate(corner_nodes):
            self._validate_point(node, f'コーナーノード{i+1}')
        
        # 断面情報の検証
        section = definition['section']
        if not isinstance(section, dict):
            raise ValueError("断面情報は辞書である必要があります")
        
        if 'section_type' not in section:
            raise ValueError("断面情報に'section_type'が必要です")
        
        return True
    
    def validate_tapered_beam(self, start_section: Any, end_section: Any) -> bool:
        """テーパー梁をバリデート
        
        Args:
            start_section: 開始断面
            end_section: 終了断面
            
        Returns:
            bool: バリデーション結果
            
        Raises:
            ValueError: バリデーションエラー
        """
        if start_section is None or end_section is None:
            raise ValueError("テーパー梁には開始断面と終了断面の両方が必要です")
        
        # 断面タイプの互換性チェック
        if hasattr(start_section, 'section_type') and hasattr(end_section, 'section_type'):
            start_type = start_section.section_type
            end_type = end_section.section_type
            
            # 基本的な互換性チェック（同じタイプか互換性のあるタイプか）
            compatible_pairs = [
                ('H', 'H'),  # H形鋼同士
                ('RECT', 'RECT'),  # 矩形断面同士
                ('BOX', 'BOX'),  # 角形鋼管同士
                ('PIPE', 'PIPE')  # 鋼管同士
            ]
            
            if (start_type, end_type) not in compatible_pairs:
                raise ValueError(f"互換性のない断面タイプの組み合わせです: {start_type} -> {end_type}")
        
        return True
    
    def _validate_point(self, point, point_name: str) -> None:
        """座標点をバリデート（辞書またはPoint3Dオブジェクト対応）
        
        Args:
            point: 座標点辞書またはPoint3Dオブジェクト
            point_name: 点の名前（エラーメッセージ用）
            
        Raises:
            ValueError: バリデーションエラー
        """
        from common.geometry import Point3D
        
        if isinstance(point, Point3D):
            # Point3Dオブジェクトの場合
            if not all(isinstance(coord, (int, float)) for coord in [point.x, point.y, point.z]):
                raise ValueError(f"{point_name}の座標は数値である必要があります")
        elif isinstance(point, dict):
            # 辞書の場合（従来の処理）
            required_coords = ['x', 'y', 'z']
            for coord in required_coords:
                if coord not in point:
                    raise ValueError(f"{point_name}に座標'{coord}'が不足しています")
                
                if not isinstance(point[coord], (int, float)):
                    raise ValueError(f"{point_name}の座標'{coord}'は数値である必要があります")
        else:
            raise ValueError(f"{point_name}は辞書またはPoint3Dオブジェクトである必要があります")
    
    def _points_are_identical(self, point1, point2, tolerance: float = 1e-6) -> bool:
        """2つの点が同一かチェック（辞書またはPoint3Dオブジェクト対応）
        
        Args:
            point1: 座標点1（辞書またはPoint3Dオブジェクト）
            point2: 座標点2（辞書またはPoint3Dオブジェクト）
            tolerance: 許容誤差
            
        Returns:
            bool: 同一の場合True
        """
        from common.geometry import Point3D
        
        # 座標値を取得するヘルパー関数
        def get_coords(point):
            if isinstance(point, Point3D):
                return point.x, point.y, point.z
            elif isinstance(point, dict):
                return point.get('x', 0), point.get('y', 0), point.get('z', 0)
            else:
                return 0, 0, 0
        
        x1, y1, z1 = get_coords(point1)
        x2, y2, z2 = get_coords(point2)
        
        return (abs(x1 - x2) <= tolerance and 
                abs(y1 - y2) <= tolerance and 
                abs(z1 - z2) <= tolerance)