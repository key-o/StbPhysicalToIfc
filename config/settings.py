from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class AppConfig:
    """アプリケーション設定クラス"""

    default_output_dir: Path = Path("output")
    debug_enabled: bool = False  # デバッグ出力制御（通常時はFalse）
    show_completion_dialog: bool = True  # EXE実行時の完了ダイアログ表示制御
    show_error_dialog: bool = True  # EXE実行時のエラーダイアログ表示制御

    def get_log_file_path(self) -> Path:
        """ログファイル出力先パスを返す"""
        output_dir = Path(self.default_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / "app.log"

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "AppConfig":
        """設定ファイルから読み込み（未実装）"""
        # 将来的にファイル読み込み実装可
        return cls()
