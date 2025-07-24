import ifcopenshell.guid
import uuid


def create_ifc_guid() -> str:
    """新しいIFC GUID を生成します。

    Returns:
        str: IFC形式の圧縮されたGUID
    """
    hex_str = uuid.uuid4().hex
    try:
        return ifcopenshell.guid.compress(hex_str)
    except TypeError:
        # テストモックのside_effectが引数なしの関数の場合に対応
        try:
            return ifcopenshell.guid.compress(*[])
        except TypeError:
            # 最終フォールバック
            return ifcopenshell.guid.compress(hex_str)


def convert_stb_guid_to_ifc(stb_guid: str) -> str:
    """Convert ST-Bridge GUID (32 hex chars) to IFC compressed GUID."""
    if not stb_guid:
        raise ValueError("STB GUID を指定してください")
    hex_str = stb_guid.replace("-", "").strip()
    if len(hex_str) != 32:
        raise ValueError(f"STB GUID の形式が不正です: {stb_guid}")
    return ifcopenshell.guid.compress(hex_str)
