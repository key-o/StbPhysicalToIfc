"""Profile Naming Standards

プロファイル命名規則の統一化
旧バージョンとの互換性を考慮した統一的な命名規則を提供
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProfileNamingStandards:
    """プロファイル命名規則の統一クラス"""

    # 旧バージョンとの互換性を重視した命名規則
    NAMING_RULES = {
        'H': {
            'prefix': 'HProfile_',
            'format': '{prefix}{width}x{height}x{web_thickness}x{flange_thickness}',
            'suffix': '_FR{flange_thickness}'
        },
        'I': {
            'prefix': 'IProfile_',
            'format': '{prefix}{width}x{height}x{web_thickness}x{flange_thickness}',
            'suffix': '_FR{flange_thickness}'
        },
        'BOX': {
            'prefix': 'BoxProfile_',
            'format': '{prefix}{width}x{height}x{thickness}',
            'suffix': ''
        },
        'RECT': {
            'prefix': 'RectProfile_',
            'format': '{prefix}{width}x{height}',
            'suffix': ''
        },
        'CIRCLE': {
            'prefix': 'CircleProfile_',
            'format': '{prefix}{diameter}',
            'suffix': ''
        },
        'L': {
            'prefix': 'LProfile_',
            'format': '{prefix}{width}x{height}x{thickness}',
            'suffix': ''
        }
    }

    @classmethod
    def get_standardized_profile_name(
        cls, 
        section_type: str, 
        dimensions: Dict[str, Any],
        compatibility_mode: str = 'legacy'
    ) -> str:
        """標準化されたプロファイル名を生成
        
        Args:
            section_type: セクションタイプ ('H', 'I', 'BOX', etc.)
            dimensions: 寸法情報辞書
            compatibility_mode: 互換性モード ('legacy' or 'modern')
            
        Returns:
            標準化されたプロファイル名
        """
        try:
            section_type = section_type.upper()
            
            if section_type not in cls.NAMING_RULES:
                logger.warning(f"Unknown section type: {section_type}, using default")
                return cls._generate_fallback_name(section_type, dimensions)
            
            rule = cls.NAMING_RULES[section_type]
            
            if compatibility_mode == 'legacy':
                # 旧バージョン互換モード（詳細な命名）
                return cls._generate_legacy_name(section_type, dimensions, rule)
            else:
                # モダンモード（簡潔な命名）
                return cls._generate_modern_name(section_type, dimensions, rule)
                
        except Exception as e:
            logger.error(f"Profile name generation failed: {e}")
            return cls._generate_fallback_name(section_type, dimensions)

    @classmethod
    def _generate_legacy_name(
        cls, 
        section_type: str, 
        dimensions: Dict[str, Any], 
        rule: Dict[str, str]
    ) -> str:
        """旧バージョン互換の詳細命名"""
        try:
            if section_type in ['H', 'I']:
                # H形鋼・I形鋼: HProfile_200.0x100.0x5.5x8.0_FR8.0
                width = float(dimensions.get('overall_width', dimensions.get('width', 0)))
                height = float(dimensions.get('overall_depth', dimensions.get('height', 0)))
                web_thickness = float(dimensions.get('web_thickness', 0))
                flange_thickness = float(dimensions.get('flange_thickness', 0))
                
                base_name = f"{rule['prefix']}{width}x{height}x{web_thickness}x{flange_thickness}"
                suffix = f"_FR{flange_thickness}"
                return base_name + suffix
                
            elif section_type == 'BOX':
                # 角形鋼管: BoxProfile_200.0x200.0x6.0
                width = float(dimensions.get('overall_width', dimensions.get('width', 0)))
                height = float(dimensions.get('overall_depth', dimensions.get('height', 0)))
                thickness = float(dimensions.get('wall_thickness', dimensions.get('thickness', 0)))
                
                return f"{rule['prefix']}{width}x{height}x{thickness}"
                
            elif section_type == 'CIRCLE':
                # 円形: CircleProfile_216.3
                diameter = float(dimensions.get('outer_diameter', dimensions.get('diameter', 0)))
                return f"{rule['prefix']}{diameter}"
                
            elif section_type == 'L':
                # L形鋼: LProfile_100.0x100.0x7.0
                width = float(dimensions.get('overall_width', dimensions.get('width', 0)))
                height = float(dimensions.get('overall_depth', dimensions.get('height', 0)))
                thickness = float(dimensions.get('thickness', 0))
                
                return f"{rule['prefix']}{width}x{height}x{thickness}"
                
            elif section_type == 'RECT':
                # 長方形: RectProfile_300.0x500.0
                width = float(dimensions.get('overall_width', dimensions.get('width', 0)))
                height = float(dimensions.get('overall_depth', dimensions.get('height', 0)))
                
                return f"{rule['prefix']}{width}x{height}"
                
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Legacy name generation failed for {section_type}: {e}")
            
        return cls._generate_fallback_name(section_type, dimensions)

    @classmethod
    def _generate_modern_name(
        cls, 
        section_type: str, 
        dimensions: Dict[str, Any], 
        rule: Dict[str, str]
    ) -> str:
        """モダンな簡潔命名"""
        try:
            if section_type in ['H', 'I']:
                # 簡潔版: H_200.0x100.0x5.5x8.0
                width = float(dimensions.get('overall_width', dimensions.get('width', 0)))
                height = float(dimensions.get('overall_depth', dimensions.get('height', 0)))
                web_thickness = float(dimensions.get('web_thickness', 0))
                flange_thickness = float(dimensions.get('flange_thickness', 0))
                
                return f"{section_type}_{width}x{height}x{web_thickness}x{flange_thickness}"
                
            elif section_type == 'BOX':
                # 簡潔版: BOX_200.0x200.0x6.0
                width = float(dimensions.get('overall_width', dimensions.get('width', 0)))
                height = float(dimensions.get('overall_depth', dimensions.get('height', 0)))
                thickness = float(dimensions.get('wall_thickness', dimensions.get('thickness', 0)))
                
                return f"{section_type}_{width}x{height}x{thickness}"
                
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Modern name generation failed for {section_type}: {e}")
            
        return cls._generate_fallback_name(section_type, dimensions)

    @classmethod
    def _generate_fallback_name(cls, section_type: str, dimensions: Dict[str, Any]) -> str:
        """フォールバック名の生成"""
        try:
            # 基本的な寸法から名前を生成
            width = dimensions.get('overall_width', dimensions.get('width', 'Unknown'))
            height = dimensions.get('overall_depth', dimensions.get('height', 'Unknown'))
            
            return f"{section_type}Profile_{width}x{height}"
            
        except Exception:
            return f"{section_type}Profile_Unknown"

    @classmethod
    def standardize_existing_name(cls, current_name: str) -> str:
        """既存の名前を標準形式に変換
        
        現在の新バージョンの名前 (H_200.0x100.0x5.5x8.0) を
        旧バージョン互換形式 (HProfile_200.0x100.0x5.5x8.0_FR8.0) に変換
        """
        try:
            # 現在の形式を解析
            if current_name.startswith('H_'):
                # H_200.0x100.0x5.5x8.0 -> HProfile_200.0x100.0x5.5x8.0_FR8.0
                dimensions_part = current_name[2:]  # "H_" を除去
                parts = dimensions_part.split('x')
                
                if len(parts) == 4:
                    width, height, web_thick, flange_thick = parts
                    return f"HProfile_{width}x{height}x{web_thick}x{flange_thick}_FR{flange_thick}"
                    
            elif current_name.startswith('I_'):
                # I形鋼も同様に処理
                dimensions_part = current_name[2:]
                parts = dimensions_part.split('x')
                
                if len(parts) == 4:
                    width, height, web_thick, flange_thick = parts
                    return f"IProfile_{width}x{height}x{web_thick}x{flange_thick}_FR{flange_thick}"
                    
            elif current_name.startswith('BOX_'):
                # BOX_200.0x200.0x6.0 -> BoxProfile_200.0x200.0x6.0
                dimensions_part = current_name[4:]  # "BOX_" を除去
                return f"BoxProfile_{dimensions_part}"
                
            # その他の形式はそのまま返す
            return current_name
            
        except Exception as e:
            logger.warning(f"Name standardization failed for '{current_name}': {e}")
            return current_name

    @classmethod
    def get_naming_mode_for_compatibility(cls) -> str:
        """互換性のための命名モードを取得"""
        # 現在は旧バージョンとの互換性を重視
        return 'legacy'