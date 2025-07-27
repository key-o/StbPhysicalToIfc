#!/usr/bin/env python3.11
"""STB to IFC 変換ツール - メインエントリーポイント

新しいアーキテクチャによる統合変換システムのエントリーポイントです。

使用例:
  python main.py                           # ファイル選択ダイアログを表示
  python main.py input.stb                 # ファイルを指定して変換
  python main.py input.stb -o output.ifc   # 出力ファイル名も指定
  python main.py --select-file             # 明示的にファイル選択ダイアログ
  python main.py --debug                   # デバッグモードでファイル選択ダイアログ
  python main.py --info input.stb          # 変換情報のみ表示
  python main.py input.stb --debug         # デバッグモードでファイル変換
"""

import sys
import os
from pathlib import Path

# 標準出力・標準エラー出力をUTF-8に統一（OS問わず）
try:
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    try:
        import io

        if sys.stdout is not None and hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        if sys.stderr is not None and hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except (AttributeError, OSError):
        pass

# PYTHONIOENCODINGを明示的に設定（OS問わず）
os.environ["PYTHONIOENCODING"] = "utf-8"

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# PyInstallerのEXE環境での追加設定
if getattr(sys, "frozen", False):
    # PyInstallerでパッケージ化された場合
    application_path = Path(sys.executable).parent
    if str(application_path) not in sys.path:
        sys.path.insert(0, str(application_path))
    # _MEIPASSディレクトリもパスに追加
    if hasattr(sys, "_MEIPASS"):
        meipass_path = Path(sys._MEIPASS)
        if str(meipass_path) not in sys.path:
            sys.path.insert(0, str(meipass_path))

try:
    from ui.cli_interface import CliInterface, show_message_box, is_exe_environment
except ImportError as e:
    error_msg = f"モジュールのインポートエラー: {e}\n"
    error_msg += "現在のPythonパス:\n"
    for path in sys.path:
        error_msg += f"  - {path}\n"

    # windowedモードでもエラーを確認できるようにファイルに出力
    try:
        with open("import_error.log", "w", encoding="utf-8") as f:
            f.write(error_msg)
    except Exception:
        pass

    # 標準出力が利用可能な場合のみ出力
    if sys.stdout is not None:
        print(error_msg)

    sys.exit(1)


def main():
    """メイン関数"""
    print("=" * 60)
    print("STB to IFC 変換ツール v2.2.0")
    print("=" * 60)

    # 引数なしの場合は自動的にファイル選択モードに
    if len(sys.argv) == 1:
        print("ファイル選択ダイアログを開きます...")
        sys.argv.append("--select-file")
    # デバッグモードのみ指定された場合もファイル選択ダイアログを表示
    elif len(sys.argv) == 2 and sys.argv[1] == "--debug":
        print("デバッグモードでファイル選択ダイアログを開きます...")
        sys.argv.append("--select-file")

    # CLIインターフェースを実行
    cli = CliInterface()
    exit_code = cli.run()

    # 最終結果メッセージ
    if exit_code == 0:
        final_message = "処理が正常に完了しました"
        print("=" * 60)
        print(final_message)
        print("=" * 60)

        # EXE環境では追加で完了メッセージを表示
        if is_exe_environment():
            show_message_box(
                "処理完了", "StbPhysicalToIfc変換ツール\n\n" + final_message, "info"
            )
    else:
        error_message = "処理中にエラーが発生しました"
        print("=" * 60)
        print(error_message)
        print("=" * 60)

        # EXE環境ではエラーメッセージボックスも表示
        if is_exe_environment():
            show_message_box(
                "処理エラー",
                "StbPhysicalToIfc変換ツール\n\n"
                + error_message
                + "\n\n詳細はerror.logファイルを確認してください。",
                "error",
            )

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n中断されました。")
        sys.exit(1)
    except Exception as e:
        error_msg = f"\n予期しないエラーが発生しました: {e}"

        # EXE環境では例外エラーもメッセージボックスで表示
        if is_exe_environment():
            show_message_box(
                "システムエラー",
                f"予期しないエラーが発生しました:\n\n{str(e)}\n\nerror.logファイルに詳細が記録されました。",
                "error",
            )

        print(error_msg)

        # windowedモードでもエラーを確認できるようにファイルに出力
        try:
            import traceback

            with open("error.log", "w", encoding="utf-8") as f:
                f.write(error_msg + "\n")
                traceback.print_exc(file=f)
        except Exception:
            pass

        # 標準出力が利用可能な場合のみトレースバックを出力
        if sys.stdout is not None:
            try:
                import traceback

                traceback.print_exc()
            except Exception:
                pass

        sys.exit(1)
