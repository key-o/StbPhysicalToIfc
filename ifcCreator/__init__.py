"""ifcCreator

v2.2.0 統合アーキテクチャ
後方互換性削除、統一アーキテクチャベース
"""

# v2.2.0: 統合アーキテクチャのみエクスポート
from .core.element_creation_factory import ElementCreationFactory
from .core.ifc_project_builder import IFCProjectBuilder
from .api import IfcCreator

__version__ = "2.2.0"

__all__ = [
    "ElementCreationFactory",
    "IFCProjectBuilder", 
    "create_combined_ifc_project",
]