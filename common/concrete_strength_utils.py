# common/concrete_strength_utils.py
"""
コンクリート強度に関するユーティリティ関数
"""
import re
from typing import Optional, Tuple


def extract_concrete_strength_value(
    strength_concrete: Optional[str],
) -> Optional[float]:
    """
    STBのコンクリート強度文字列（例: "Fc21", "Fc30", "Fc36"）から
    数値（N/mm²）を抽出する

    Args:
        strength_concrete: STBのコンクリート強度文字列

    Returns:
        コンクリート強度の数値（N/mm²）、抽出できない場合はNone

    Examples:
        >>> extract_concrete_strength_value("Fc21")
        21.0
        >>> extract_concrete_strength_value("Fc30")
        30.0
        >>> extract_concrete_strength_value("Fc36")
        36.0
        >>> extract_concrete_strength_value("invalid")
        None
    """
    if not strength_concrete:
        return None

    # "Fc" で始まる数値を抽出（例: Fc21 -> 21）
    match = re.match(r"^Fc(\d+(?:\.\d+)?)$", strength_concrete, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    # 数値のみの場合（例: "21" -> 21）
    try:
        return float(strength_concrete)
    except ValueError:
        return None


def convert_strength_to_pascals(strength_nmm2: float) -> float:
    """
    コンクリート強度をN/mm²からPa（パスカル）に変換する

    Args:
        strength_nmm2: コンクリート強度（N/mm²）

    Returns:
        コンクリート強度（Pa）

    Examples:
        >>> convert_strength_to_pascals(21.0)
        21000000.0
        >>> convert_strength_to_pascals(30.0)
        30000000.0
    """
    # 1 N/mm² = 1,000,000 Pa
    return strength_nmm2 * 1_000_000


def format_concrete_strength_name(strength_concrete: Optional[str]) -> str:
    """
    STBのコンクリート強度文字列をIFC材料名として適切な形式にフォーマットする

    Args:
        strength_concrete: STBのコンクリート強度文字列

    Returns:
        IFC材料名（例: "Concrete_Fc21"）
    """
    if not strength_concrete:
        return "Concrete"

    # すでに適切な形式の場合はそのまま返す
    if strength_concrete.startswith("Concrete_"):
        return strength_concrete

    # Fcで始まる場合は"Concrete_"を前置
    if strength_concrete.upper().startswith("FC"):
        return f"Concrete_{strength_concrete}"

    # 数値のみの場合は"Concrete_Fc"を前置
    try:
        float(strength_concrete)
        return f"Concrete_Fc{strength_concrete}"
    except ValueError:
        # その他の場合は"Concrete_"を前置
        return f"Concrete_{strength_concrete}"


def parse_concrete_strength_info(
    strength_concrete: Optional[str],
) -> Tuple[str, Optional[float], Optional[float]]:
    """
    STBのコンクリート強度文字列から、IFC用の情報を一括取得する

    Args:
        strength_concrete: STBのコンクリート強度文字列（例: "Fc21"）

    Returns:
        タプル: (材料名, 強度値_N/mm², 強度値_Pa)

    Examples:
        >>> parse_concrete_strength_info("Fc21")
        ("Concrete_Fc21", 21.0, 21000000.0)
        >>> parse_concrete_strength_info("Fc30")
        ("Concrete_Fc30", 30.0, 30000000.0)
        >>> parse_concrete_strength_info("invalid")
        ("Concrete_invalid", None, None)
    """
    material_name = format_concrete_strength_name(strength_concrete)
    strength_nmm2 = extract_concrete_strength_value(strength_concrete)
    strength_pa = (
        convert_strength_to_pascals(strength_nmm2)
        if strength_nmm2 is not None
        else None
    )

    return material_name, strength_nmm2, strength_pa
