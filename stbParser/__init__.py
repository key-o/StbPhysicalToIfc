# __init__.py
"""
ST-Bridge Parser Package

ST-Bridge XMLファイルから構造要素を抽出し、IFC形式に変換するためのパッケージ
"""

# 新しい統合パーサー（推奨）
from .unified_stb_parser import UnifiedSTBParser, ElementType

__all__ = [
    # 新しい統合パーサー（推奨）
    "UnifiedSTBParser",
    "ElementType",
]
