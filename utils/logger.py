import logging
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str, log_file: Optional[Path] = None, debug_enabled: bool = False
) -> logging.Logger:
    """ロガーを設定して返します。"""
    logger = logging.getLogger(name)

    # 既に設定されている場合は設定をスキップ
    if logger.handlers:
        return logger

    # デバッグが有効でない場合はINFOレベルに設定
    logger.setLevel(logging.DEBUG if debug_enabled else logging.INFO)

    # ルートロガーのレベルも設定（子ロガーでのデバッグ出力を確保）
    if debug_enabled:
        logging.getLogger().setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # コンソール出力ハンドラ
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # ファイル出力ハンドラ
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """既存のロガーを取得、なければ作成"""
    return logging.getLogger(name)
