#!/usr/bin/env python3
"""大梁配置位置修正の検証テスト

修正内容: ifcCreator/creators/beam_creator.py の lines 452-459
はりせい分のZ方向オフセット (center_z -= vdim / 2.0) を削除
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ifcCreator.creators.beam_creator import BeamCreator
from ifcCreator.project_builder import IFCProjectBuilder
from ifcCreator.utils.structural_section import StructuralSection
from common.geometry import Point3D
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_beam_placement_fix():
    """大梁配置位置修正のテスト"""
    print("=" * 80)
    print("大梁配置位置修正の検証テスト")
    print("=" * 80)
    
    try:
        # プロジェクトビルダー初期化
        project_builder = IFCProjectBuilder()
        project_builder.create_project_structure("BeamPlacementTest", "Test Author")
        
        # 梁作成クラス初期化
        beam_creator = BeamCreator(project_builder)
        
        # テスト用断面定義 (H形鋼)
        test_section = StructuralSection(
            name="H-400x200x8x12",
            section_type="H",
            overall_depth=400.0,    # はりせい 400mm
            overall_width=200.0,
            web_thickness=8.0,
            flange_thickness=12.0
        )
        
        # テスト用座標
        start_point = Point3D(0.0, 0.0, 3000.0)    # 3階レベル
        end_point = Point3D(6000.0, 0.0, 3000.0)   # 6m スパン
        
        print(f"\nテスト条件:")
        print(f"開始点: ({start_point.x}, {start_point.y}, {start_point.z})")
        print(f"終了点: ({end_point.x}, {end_point.y}, {end_point.z})")
        print(f"はりせい: {test_section.properties.get('overall_depth')}mm")
        
        # 期待される配置座標 (修正後)
        expected_center_x = (start_point.x + end_point.x) / 2.0  # 3000.0
        expected_center_y = (start_point.y + end_point.y) / 2.0  # 0.0
        expected_center_z = (start_point.z + end_point.z) / 2.0  # 3000.0 (はりせい調整なし)
        
        print(f"\n期待される配置座標 (修正後):")
        print(f"X: {expected_center_x}")
        print(f"Y: {expected_center_y}")  
        print(f"Z: {expected_center_z} (はりせい調整なし)")
        
        # 梁作成実行
        print(f"\n梁作成実行中...")
        beam = beam_creator.create_beam(
            start_point=start_point,
            end_point=end_point,
            sec_start=test_section,
            beam_name="TestBeam_Fixed",
            beam_tag="B_FIX_001"
        )
        
        if beam:
            print(f"✓ 梁作成成功: {beam.Name}")
            
            # 配置座標の確認
            placement = beam.ObjectPlacement
            if placement and hasattr(placement, "RelativePlacement"):
                rel_placement = placement.RelativePlacement
                if hasattr(rel_placement, "Location"):
                    location = rel_placement.Location
                    if hasattr(location, "Coordinates"):
                        actual_coords = location.Coordinates
                        actual_x, actual_y, actual_z = actual_coords
                        
                        print(f"\n実際の配置座標:")
                        print(f"X: {actual_x}")
                        print(f"Y: {actual_y}")
                        print(f"Z: {actual_z}")
                        
                        # 座標比較
                        diff_x = abs(actual_x - expected_center_x)
                        diff_y = abs(actual_y - expected_center_y)
                        diff_z = abs(actual_z - expected_center_z)
                        
                        print(f"\n座標差分:")
                        print(f"ΔX: {diff_x:.3f}mm")
                        print(f"ΔY: {diff_y:.3f}mm")
                        print(f"ΔZ: {diff_z:.3f}mm")
                        
                        # 修正検証
                        tolerance = 1.0  # 1mm許容誤差
                        
                        if diff_x < tolerance and diff_y < tolerance and diff_z < tolerance:
                            print(f"\n✅ 修正成功!")
                            print(f"配置座標が期待値と一致しています (許容誤差: {tolerance}mm)")
                            
                            # はりせい調整が適用されていないことを確認
                            beam_depth = test_section.properties.get("overall_depth", 0.0)
                            old_z_adjustment = beam_depth / 2.0  # 旧実装での調整値
                            
                            print(f"\n確認:")
                            print(f"はりせい: {beam_depth}mm")
                            print(f"旧実装での調整: -{old_z_adjustment}mm")
                            print(f"Z座標に調整が適用されていないため、修正成功")
                            
                            return True
                        else:
                            print(f"\n❌ 修正失敗")
                            print(f"配置座標に許容範囲を超える差分があります")
                            return False
                        
        else:
            print(f"❌ 梁作成失敗")
            return False
            
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        return False

def main():
    """メイン実行"""
    print("大梁配置位置修正の検証テストを開始...")
    
    success = test_beam_placement_fix()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 検証テスト成功!")
        print("大梁配置位置の修正が正常に動作しています")
    else:
        print("❌ 検証テスト失敗")
        print("修正内容を再確認してください")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)