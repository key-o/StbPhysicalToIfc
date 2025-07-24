"""Utility functions for JSON serialization.
"""
from typing import Any
import json


def save_json(data: Any, file_path: str) -> None:
    """Save Python data to a JSON file using UTF-8 encoding.

    Args:
        data: JSON serializable object to save.
        file_path: Destination path for the JSON file.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

