"""コマンドラインインターフェース

変換APIを使用したCLIインターフェースを提供します。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List

from core.conversion_api import Stb2IfcConverter
from exceptions.custom_errors import Stb2IfcError
from config.settings import AppConfig


def show_message_box(
    title: str, message: str, message_type: str = "info", force_show: bool = False
):
    """メッセージボックスを表示（EXE環境対応）

    Args:
        title: メッセージボックスのタイトル
        message: 表示するメッセージ
        message_type: メッセージの種類 ("info", "error", "warning")
        force_show: 設定に関係なく強制的に表示するかどうか
    """
    # 設定確認
    config = AppConfig()

    # 強制表示でない場合は設定に従う
    if not force_show:
        if message_type == "error" and not config.show_error_dialog:
            return
        if message_type == "info" and not config.show_completion_dialog:
            return

    try:
        # PyInstallerのwindowedモードでも表示されるようにtkinterを使用
        import tkinter as tk
        from tkinter import messagebox

        # 一時的なrootウィンドウを作成（非表示）
        root = tk.Tk()
        root.withdraw()  # メインウィンドウを非表示
        root.attributes("-topmost", True)  # 最前面に表示

        if message_type == "error":
            messagebox.showerror(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)

        root.destroy()

    except Exception:
        # tkinterが使用できない場合は標準出力に出力
        print(f"{title}: {message}")


def is_exe_environment():
    """PyInstallerのEXE環境かどうかを判定"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


class CliInterface:
    """コマンドラインインターフェース"""

    def __init__(self):
        self.converter = None

    def create_parser(self) -> argparse.ArgumentParser:
        """引数パーサーを作成"""
        parser = argparse.ArgumentParser(
            description="ST-Bridge to IFC変換ツール",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用例:
  python stb2ifc_cli.py input.stb                    # input.stbをinput.ifcに変換
  python stb2ifc_cli.py input.stb -o output.ifc      # 出力ファイル名を指定
  python stb2ifc_cli.py input.stb --debug             # デバッグモードで実行
  python stb2ifc_cli.py --info input.stb              # 変換情報のみ表示
            """,
        )

        parser.add_argument("input_file", nargs="?", help="入力STBファイルパス")

        parser.add_argument(
            "-o",
            "--output",
            dest="output_file",
            help="出力IFCファイルパス（省略時は入力ファイル名.ifc）",
        )

        parser.add_argument(
            "--debug", action="store_true", help="デバッグモードを有効にする"
        )

        parser.add_argument(
            "--info", action="store_true", help="変換情報のみ表示（変換は行わない）"
        )

        parser.add_argument(
            "--select-file", action="store_true", help="ファイル選択ダイアログを使用"
        )

        parser.add_argument(
            "--categories",
            type=str,
            help="変換対象カテゴリをカンマ区切りで指定 (例: beam,column,wall)\n"
            "有効なカテゴリ: beam, column, brace, wall, slab, footing, pile, foundation_column",
        )

        return parser

    def run(self, args: Optional[list] = None) -> int:
        """CLIを実行

        Args:
            args: コマンドライン引数（テスト用）

        Returns:
            int: 終了コード（0: 成功、1: エラー）
        """
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        try:
            # 変換器を初期化
            self.converter = Stb2IfcConverter(debug_enabled=parsed_args.debug)

            # カテゴリの処理
            selected_categories = None
            if parsed_args.categories:
                selected_categories = [
                    cat.strip() for cat in parsed_args.categories.split(",")
                ]
                print(f"変換対象カテゴリ: {', '.join(selected_categories)}")

            # 入力ファイルの取得
            input_file = self._get_input_file(parsed_args)
            if not input_file:
                parser.print_help()
                return 1

            # 変換情報のみ表示
            if parsed_args.info:
                return self._show_info(input_file, selected_categories)

            # 変換実行
            return self._convert_file(
                input_file, parsed_args.output_file, selected_categories
            )

        except Stb2IfcError as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"予期しないエラー: {e}", file=sys.stderr)
            return 1

    def _get_input_file(self, args) -> Optional[str]:
        """入力ファイルを取得"""
        if args.input_file:
            return args.input_file

        if args.select_file:
            # ファイル選択UIを使用
            return self._select_file_with_ui()

        # デフォルトファイルを使用
        return self._get_default_file()

    def _select_file_with_ui(self) -> Optional[str]:
        """ファイル選択UIを使用"""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()

            file_path = filedialog.askopenfilename(
                title="STBファイルを選択してください",
                filetypes=[("STBファイル", "*.stb"), ("全てのファイル", "*.*")],
                initialdir="sampleStb",
            )

            root.destroy()
            return file_path if file_path else None

        except ImportError:
            print("tkinterが利用できません。デフォルトファイルを使用します。")
            return self._get_default_file()

    def _get_default_file(self) -> Optional[str]:
        """デフォルトファイルを取得"""
        default_files = [
            "sampleStb/建物モデル/Sサンプルv202_20250317.stb",
            "sampleStb/建物モデル/RCサンプルv202_20250317.stb",
            "sampleStb/Column/S_Column_H.stb",
            "sampleStb/Beam/S_Beam_straightH.stb",
        ]

        for file_path in default_files:
            if Path(file_path).exists():
                print(f"デフォルトファイルを使用: {file_path}")
                return file_path

        # sampleStbディレクトリから探す
        sample_dir = Path("sampleStb")
        if sample_dir.exists():
            stb_files = list(sample_dir.rglob("*.stb"))
            if stb_files:
                file_path = str(stb_files[0])
                print(f"最初に見つかったファイルを使用: {file_path}")
                return file_path

        return None

    def _show_info(
        self, input_file: str, selected_categories: Optional[List[str]] = None
    ) -> int:
        """変換情報を表示"""
        try:
            info = self.converter.get_conversion_info(input_file, selected_categories)

            print("=== STB to IFC 変換情報 ===")
            print(f"入力ファイル: {info['input_file']}")
            if selected_categories:
                print(f"変換対象カテゴリ: {', '.join(selected_categories)}")
            print("要素数:")

            total_elements = 0
            for element_type, count in info["element_counts"].items():
                print(f"  {element_type}: {count}")
                if isinstance(count, int):
                    total_elements += count

            print(f"合計: {total_elements} 要素")
            return 0

        except Exception as e:
            print(f"情報取得エラー: {e}", file=sys.stderr)
            return 1

    def _convert_file(
        self,
        input_file: str,
        output_file: Optional[str],
        selected_categories: Optional[List[str]] = None,
    ) -> int:
        """ファイル変換を実行"""
        try:
            output_path = self.converter.convert_file(
                input_file, output_file, selected_categories
            )

            # 成功メッセージを表示
            success_message = f"変換が正常に完了しました！\n\n入力ファイル: {input_file}\n出力ファイル: {output_path}"

            # EXE環境の場合はメッセージボックスを表示
            if is_exe_environment():
                show_message_box("変換完了", success_message, "info")

            # 常に標準出力にも出力（コンソール環境用）
            print(f"変換完了: {output_path}")

            return 0

        except Exception as e:
            error_message = f"変換中にエラーが発生しました:\n\n{str(e)}\n\n入力ファイル: {input_file}"

            # EXE環境の場合はエラーメッセージボックスを表示
            if is_exe_environment():
                show_message_box("変換エラー", error_message, "error")

            # 常に標準エラー出力にも出力
            print(f"変換エラー: {e}", file=sys.stderr)
            return 1


def main():
    """メイン関数"""
    cli = CliInterface()
    exit_code = cli.run()
    sys.exit(exit_code)
