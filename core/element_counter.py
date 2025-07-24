"""STB要素とIFC要素の数量比較機能"""

import re
from typing import Dict, Tuple
from stbParser.unified_stb_parser import UnifiedSTBParser, ElementType


class ElementCounter:
    """STB要素とIFC要素の数量比較を行うクラス"""
    
    def __init__(self):
        pass
    
    def count_stb_elements(self, stb_content: str) -> Dict[str, int]:
        """STB要素の数量をカウント"""
        parser = UnifiedSTBParser(stb_content)
        
        counts = {}
        for element_type in ElementType:
            count = parser.get_element_count(element_type)
            counts[element_type.value] = count
        
        return counts
    
    def count_ifc_elements(self, ifc_content: str) -> Dict[str, int]:
        """IFC要素の数量をカウント"""
        counts = {
            'beam': 0,
            'column': 0,
            'slab': 0,
            'wall': 0,
            'brace': 0,
            'pile': 0,
            'footing': 0,
            'foundation_column': 0,
            'assembly': 0,  # SRC用のアセンブリ
        }
        
        # 正規表現でIFC要素をカウント
        patterns = {
            'beam': r'IFCBEAM\(',
            'column': r'IFCCOLUMN\(',
            'slab': r'IFCSLAB\(',
            'wall': r'IFCWALL\(',
            'brace': r'IFCMEMBER\([^)]*\'[^\']*BRACE',  # IFCMEMBERでBRACEを含む
            'pile': r'IFCPILE\(',
            'footing': r'IFCFOOTINGELEMENT\(',
            'foundation_column': r'IFCCOLUMN\([^)]*\'[^\']*FOUNDATION',  # 基礎柱
            'assembly': r'IFCELEMENTASSEMBLY\(',  # SRC複合要素
        }
        
        for element_type, pattern in patterns.items():
            matches = re.findall(pattern, ifc_content, re.IGNORECASE)
            counts[element_type] = len(matches)
        
        return counts
    
    def compare_conversion(self, stb_content: str, ifc_content: str) -> Dict:
        """STBとIFCの要素数を比較し、変換効率を分析"""
        stb_counts = self.count_stb_elements(stb_content)
        ifc_counts = self.count_ifc_elements(ifc_content)
        
        # 対応関係マッピング
        mapping = {
            'beam': 'beam',
            'column': 'column', 
            'slab': 'slab',
            'wall': 'wall',
            'brace': 'brace',
            'pile': 'pile',
            'footing': 'footing',
            'foundation_column': 'foundation_column',
        }
        
        comparison = {}
        total_stb = 0
        total_ifc_primary = 0
        
        for stb_type, ifc_type in mapping.items():
            stb_count = stb_counts.get(stb_type, 0)
            ifc_count = ifc_counts.get(ifc_type, 0)
            
            total_stb += stb_count
            total_ifc_primary += ifc_count
            
            if stb_count > 0:
                conversion_rate = (ifc_count / stb_count) * 100
                comparison[stb_type] = {
                    'stb_count': stb_count,
                    'ifc_count': ifc_count,
                    'conversion_rate': conversion_rate,
                    'status': 'OK' if conversion_rate >= 100 else 'PARTIAL' if conversion_rate > 0 else 'FAILED'
                }
        
        # SRC要素の特別処理
        src_count = stb_counts.get('src', 0)
        assembly_count = ifc_counts.get('assembly', 0)
        
        if src_count > 0:
            comparison['src'] = {
                'stb_count': src_count,
                'ifc_count': assembly_count,
                'conversion_rate': (assembly_count / src_count) * 100 if src_count > 0 else 0,
                'status': 'SRC_ASSEMBLY'
            }
        
        # 全体統計
        total_ifc_all = sum(ifc_counts.values())
        overall_rate = (total_ifc_primary / total_stb) * 100 if total_stb > 0 else 0
        
        comparison['summary'] = {
            'total_stb_elements': total_stb,
            'total_ifc_primary': total_ifc_primary,
            'total_ifc_all': total_ifc_all,
            'overall_conversion_rate': overall_rate,
            'src_elements': src_count,
            'assembly_elements': assembly_count
        }
        
        return comparison
    
    def print_comparison_report(self, comparison: Dict):
        """比較結果をレポート形式で出力"""
        print("=" * 60)
        print("STB to IFC 変換比較レポート")
        print("=" * 60)
        
        # 個別要素の比較
        for element_type, data in comparison.items():
            if element_type == 'summary':
                continue
                
            stb_count = data['stb_count']
            ifc_count = data['ifc_count']
            rate = data['conversion_rate']
            status = data['status']
            
            if stb_count > 0:  # STB要素が存在する場合のみ表示
                print(f"{element_type.upper():15} STB:{stb_count:3d} → IFC:{ifc_count:3d} ({rate:5.1f}%) [{status}]")
        
        print("-" * 60)
        
        # 全体統計
        summary = comparison.get('summary', {})
        total_stb = summary.get('total_stb_elements', 0)
        total_ifc = summary.get('total_ifc_primary', 0)
        overall_rate = summary.get('overall_conversion_rate', 0)
        src_count = summary.get('src_elements', 0)
        assembly_count = summary.get('assembly_elements', 0)
        
        print(f"合計              STB:{total_stb:3d} → IFC:{total_ifc:3d} ({overall_rate:5.1f}%)")
        
        if src_count > 0:
            print(f"SRC複合要素       STB:{src_count:3d} → Assembly:{assembly_count:3d}")
        
        print("=" * 60)
        
        # 変換状況の評価
        if overall_rate >= 100:
            print("✅ 優良な変換効率です")
        elif overall_rate >= 80:
            print("⚠️  許容範囲の変換効率です")
        else:
            print("❌ 変換効率の改善が必要です")
        
        print("=" * 60)