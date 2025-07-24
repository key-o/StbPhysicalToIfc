"""STBファイルの読み込み・処理を行うサービス"""

import os
from typing import Optional

from utils.logger import get_logger
from exceptions.custom_errors import FileNotFoundError, ConversionError, FileSizeError


class StbFileService:
    """STBファイルの読み込み・検証を行うサービス"""
    
    # セキュリティ設定
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__)
    
    def load_stb_file(self, file_path: str) -> str:
        """STBファイルを読み込み、内容を返す"""
        # ファイル存在確認
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"ST-Bridge ファイルが {file_path} に見つかりません"
            )
        
        # ファイルサイズ検証（セキュリティ対策）
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise FileSizeError(
                f"ファイルサイズが制限を超えています: {file_size / (1024*1024):.1f}MB > {self.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        stb_xml_content: Optional[str] = None
        
        # UTF-8エンコーディングで読み込み試行
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                stb_xml_content = f.read()
            self.logger.info(
                "読み込んだ ST-Bridge ファイル: %s (エンコーディング: utf-8)", file_path
            )
        except UnicodeDecodeError:
            self.logger.info(
                "UTF-8 での読み込みに失敗したため Shift_JIS (CP932) を試行します..."
            )
            # Shift_JISエンコーディングで読み込み試行
            try:
                with open(file_path, "r", encoding="cp932") as f:
                    stb_xml_content = f.read()
                self.logger.info(
                    "読み込んだ ST-Bridge ファイル: %s (エンコーディング: cp932)",
                    file_path,
                )
            except UnicodeDecodeError as e:
                raise ConversionError(
                    f"UTF-8 と Shift_JIS の双方で ST-Bridge ファイルを読み取れませんでした: {e}"
                ) from e
            except IOError as e:
                raise ConversionError(f"ファイル読み込みエラー (cp932): {e}") from e
        except IOError as e:
            raise ConversionError(f"ファイル読み込みエラー (utf-8): {e}") from e
        
        if stb_xml_content is None:
            raise ConversionError(
                "ST-Bridge ファイルをいずれのエンコーディングでも読み取れませんでした"
            )
        
        return stb_xml_content