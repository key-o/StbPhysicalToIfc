"""Structural Section

v2.2.0 統合構造断面クラス
最小限の実装で依存関係を削減
統一プロファイル命名規則対応
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StructuralSection:
    """統合構造断面クラス
    
    v2.2.0: 最小限の実装で依存関係を削減
    統一プロファイル命名規則対応
    """
    
    def __init__(self, name: str = "", section_type: str = "", **properties):
        """初期化
        
        Args:
            name: 断面名
            section_type: 断面タイプ
            **properties: その他プロパティ
        """
        self.name = name
        self.section_type = section_type
        self.properties = properties
        
        # 便利プロパティ（動的アクセス用）
        for key, value in properties.items():
            setattr(self, key, value)
        
    def __eq__(self, other):
        """等価比較"""
        if not isinstance(other, StructuralSection):
            return False
        return (self.name == other.name and 
                self.section_type == other.section_type and
                self.properties == other.properties)
    
    def __ne__(self, other):
        """非等価比較"""
        return not self.__eq__(other)
    
    def __str__(self):
        """文字列表現"""
        return f"StructuralSection(name='{self.name}', type='{self.section_type}')"
    
    def __repr__(self):
        """文字列表現（デバッグ用）"""
        return self.__str__()
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """プロパティを取得"""
        return self.properties.get(key, default)
    
    def set_property(self, key: str, value: Any):
        """プロパティを設定"""
        self.properties[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'name': self.name,
            'section_type': self.section_type,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuralSection':
        """辞書から作成"""
        # STBデータは'stb_name'キーを使用するため、'name'にマッピング
        name = data.get('name', data.get('stb_name', ''))
        section_type = data.get('section_type', '')
        
        # プロパティ抽出: 'properties'キーがある場合はそれを使用、
        # ない場合は辞書全体から'name'と'section_type'以外をプロパティとして使用
        if 'properties' in data:
            properties = data['properties']
        else:
            # フラット構造の場合、name/section_type以外をプロパティとする
            reserved_keys = {'name', 'section_type', 'stb_name'}
            properties = {k: v for k, v in data.items() if k not in reserved_keys}
        
        return cls(
            name=name,
            section_type=section_type,
            **properties
        )
    
    def get_standardized_profile_name(self, compatibility_mode: str = 'legacy') -> str:
        """統一プロファイル命名規則に基づく名前を取得
        
        Args:
            compatibility_mode: 互換性モード ('legacy' or 'modern')
            
        Returns:
            標準化されたプロファイル名
        """
        try:
            from common.profile_naming_standards import ProfileNamingStandards
            
            # 現在のプロパティから寸法情報を抽出
            dimensions = {
                'overall_width': getattr(self, 'overall_width', getattr(self, 'width', 0)),
                'overall_depth': getattr(self, 'overall_depth', getattr(self, 'height', 0)),
                'web_thickness': getattr(self, 'web_thickness', 0),
                'flange_thickness': getattr(self, 'flange_thickness', 0),
                'wall_thickness': getattr(self, 'wall_thickness', getattr(self, 'thickness', 0)),
                'outer_diameter': getattr(self, 'outer_diameter', getattr(self, 'diameter', 0)),
                'thickness': getattr(self, 'thickness', 0),
                'width': getattr(self, 'width', 0),
                'height': getattr(self, 'height', 0),
                'diameter': getattr(self, 'diameter', 0)
            }
            
            return ProfileNamingStandards.get_standardized_profile_name(
                self.section_type, 
                dimensions, 
                compatibility_mode
            )
            
        except ImportError:
            logger.warning("ProfileNamingStandards not available, using fallback name")
            return self.name or f"{self.section_type}Profile_Unknown"
        except Exception as e:
            logger.error(f"Failed to generate standardized profile name: {e}")
            return self.name or f"{self.section_type}Profile_Error"