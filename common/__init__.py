"""
共通モジュールパッケージ
"""

from .json_utils import save_json

try:
    from .guid_utils import convert_stb_guid_to_ifc
    __all__ = ["save_json", "convert_stb_guid_to_ifc"]
except ImportError:
    __all__ = ["save_json"]
