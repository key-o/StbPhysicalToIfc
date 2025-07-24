#!/usr/bin/env python3
"""
IFC Validator を使用したIFCファイル検証スクリプト

このスクリプトは以下の機能を提供します：
1. IFC構文検証（IFC-validator使用）
2. ジオメトリ検証
3. スキーマ適合性検証
4. BIMVision互換性チェック
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional


def run_ifc_validator(ifc_file_path: str, output_dir: Optional[str] = None) -> Dict:
    """
    IFC Validator を実行してIFCファイルを検証

    Args:
        ifc_file_path: 検証するIFCファイルのパス
        output_dir: 出力ディレクトリ（指定しない場合は一時ディレクトリ）

    Returns:
        検証結果の辞書
    """
    print("=== IFC Validator による検証 ===")

    # IFC Validatorの実行可能ファイルを探す
    validator_paths = [
        "ifc-validator",  # パスが通っている場合
        "ifcvalidator",
        "./tools/ifc-validator",
        "./tools/ifcvalidator.exe",
        "C:/Program Files/IFC Validator/ifcvalidator.exe",
    ]

    validator_exe = None
    for path in validator_paths:
        try:
            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                validator_exe = path
                print(f"IFC Validator found: {path}")
                break
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue

    if not validator_exe:
        print("⚠️ IFC Validator が見つかりません")
        print("以下の方法でインストールしてください：")
        print("1. https://github.com/buildingSMART/ifc-validator からダウンロード")
        print("2. npm install -g @buildingsmart/ifc-validator")
        print("3. パスを通すか、このスクリプトと同じディレクトリに配置")
        return {"error": "IFC Validator not found"}

    # 出力ディレクトリの準備
    if not output_dir:
        output_dir = "./validation_output"
    os.makedirs(output_dir, exist_ok=True)

    # IFC Validator実行
    output_file = os.path.join(output_dir, "validation_result.json")

    try:
        print(f"検証中: {ifc_file_path}")
        cmd = [
            validator_exe,
            "--input",
            ifc_file_path,
            "--output",
            output_file,
            "--format",
            "json",
            "--schema",
            "IFC4",  # IFC4スキーマで検証
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("✅ IFC Validator 実行完了")

            # 結果ファイルを読み込み
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    validation_result = json.load(f)
                return validation_result
            else:
                return {"status": "completed", "stdout": result.stdout}
        else:
            print(f"❌ IFC Validator 実行失敗 (code: {result.returncode})")
            print(f"stderr: {result.stderr}")
            return {"error": result.stderr, "stdout": result.stdout}

    except subprocess.TimeoutExpired:
        print("❌ IFC Validator 実行タイムアウト")
        return {"error": "Timeout"}
    except Exception as e:
        print(f"❌ IFC Validator 実行エラー: {e}")
        return {"error": str(e)}


def validate_with_ifcopenshell(ifc_file_path: str) -> Dict:
    """
    ifcopenshell を使用した基本検証
    """
    print("\n=== ifcopenshell による基本検証 ===")

    try:
        import ifcopenshell

        print("✅ ifcopenshell ライブラリ読み込み成功")
    except ImportError:
        print("❌ ifcopenshell がインストールされていません")
        return {"error": "ifcopenshell not installed"}

    try:
        # IFCファイルを読み込み
        ifc_file = ifcopenshell.open(ifc_file_path)  # type: ignore
        print("✅ IFCファイル読み込み成功")

        # 基本統計
        entity_count = len(list(ifc_file))  # type: ignore
        print(f"📊 総エンティティ数: {entity_count}")

        # 主要要素の数を確認
        element_counts = {}
        for entity_type in [
            "IfcProject",
            "IfcSite",
            "IfcBuilding",
            "IfcBuildingStorey",
            "IfcBeam",
            "IfcColumn",
            "IfcSlab",
            "IfcWall",
        ]:
            count = len(ifc_file.by_type(entity_type))  # type: ignore
            element_counts[entity_type] = count
            print(f"📊 {entity_type}: {count}")

        # スキーマバージョン確認
        schema = ifc_file.schema  # type: ignore
        print(f"📊 IFCスキーマ: {schema}")

        # プロジェクト情報
        projects = ifc_file.by_type("IfcProject")  # type: ignore
        if projects:
            project = projects[0]
            print(f"📊 プロジェクト名: {project.Name}")
            print(f"📊 プロジェクトID: {project.GlobalId}")

        return {
            "status": "success",
            "entity_count": entity_count,
            "element_counts": element_counts,
            "schema": schema,
            "project_info": {
                "name": project.Name if projects else None,
                "id": project.GlobalId if projects else None,
            },
        }

    except Exception as e:
        print(f"❌ ifcopenshell検証エラー: {e}")
        return {"error": str(e)}


def check_bim_vision_compatibility(ifc_file_path: str) -> Dict:
    """
    BIMVision互換性チェック
    """
    print("\n=== BIMVision互換性チェック ===")

    checks = []

    # ファイルパスチェック
    if any(ord(c) > 127 for c in ifc_file_path):
        checks.append(
            {
                "check": "ファイルパス文字コード",
                "status": "⚠️",
                "message": "ファイルパスに非ASCII文字が含まれています。BIMVisionで問題が発生する可能性があります。",
            }
        )
    else:
        checks.append(
            {
                "check": "ファイルパス文字コード",
                "status": "✅",
                "message": "ファイルパスは問題ありません。",
            }
        )

    # ファイルサイズチェック
    file_size = os.path.getsize(ifc_file_path)
    if file_size > 100 * 1024 * 1024:  # 100MB
        checks.append(
            {
                "check": "ファイルサイズ",
                "status": "⚠️",
                "message": f"ファイルサイズが大きいです ({file_size/1024/1024:.1f}MB)。読み込みに時間がかかる可能性があります。",
            }
        )
    else:
        checks.append(
            {
                "check": "ファイルサイズ",
                "status": "✅",
                "message": f"ファイルサイズは適切です ({file_size/1024:.1f}KB)。",
            }
        )

    # IFCバージョンチェック
    try:
        with open(ifc_file_path, "r", encoding="utf-8") as f:
            header = f.read(1000)

        if "IFC4" in header:
            checks.append(
                {
                    "check": "IFCバージョン",
                    "status": "✅",
                    "message": "IFC4形式です。BIMVisionでサポートされています。",
                }
            )
        elif "IFC2X3" in header:
            checks.append(
                {
                    "check": "IFCバージョン",
                    "status": "✅",
                    "message": "IFC2X3形式です。BIMVisionでサポートされています。",
                }
            )
        else:
            checks.append(
                {
                    "check": "IFCバージョン",
                    "status": "⚠️",
                    "message": "IFCバージョンが不明です。",
                }
            )
    except Exception as e:
        checks.append(
            {
                "check": "IFCバージョン",
                "status": "❌",
                "message": f"ヘッダー読み込みエラー: {e}",
            }
        )

    # 結果表示
    for check in checks:
        print(f"{check['status']} {check['check']}: {check['message']}")

    return {"checks": checks}


def main():
    parser = argparse.ArgumentParser(description="IFCファイル検証スクリプト")
    parser.add_argument(
        "ifc_file",
        nargs="?",
        default="sampleStb/建物モデル/CFTテスト_2.ifc",
        help="検証するIFCファイルパス",
    )
    parser.add_argument("--output", "-o", help="結果出力ディレクトリ")
    parser.add_argument(
        "--validator-only", action="store_true", help="IFC Validatorのみ実行"
    )
    parser.add_argument(
        "--ifcopenshell-only", action="store_true", help="ifcopenshellのみ実行"
    )

    args = parser.parse_args()

    ifc_file_path = args.ifc_file

    # ファイル存在確認
    if not os.path.exists(ifc_file_path):
        print(f"❌ ファイルが見つかりません: {ifc_file_path}")
        sys.exit(1)

    print(f"🔍 IFCファイル検証開始: {ifc_file_path}")
    print("=" * 60)

    results = {}

    # IFC Validator実行
    if not args.ifcopenshell_only:
        validator_result = run_ifc_validator(ifc_file_path, args.output)
        results["ifc_validator"] = validator_result

    # ifcopenshell検証
    if not args.validator_only:
        ifcopenshell_result = validate_with_ifcopenshell(ifc_file_path)
        results["ifcopenshell"] = ifcopenshell_result

        # BIMVision互換性チェック
        bimvision_result = check_bim_vision_compatibility(ifc_file_path)
        results["bimvision"] = bimvision_result

    # 結果保存
    if args.output:
        output_dir = args.output
    else:
        output_dir = "./validation_output"

    os.makedirs(output_dir, exist_ok=True)
    result_file = os.path.join(output_dir, "complete_validation_result.json")

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📄 詳細な結果を保存しました: {result_file}")

    # 総合評価
    print("\n" + "=" * 60)
    print("🏁 検証完了 - 総合評価")
    print("=" * 60)

    if "ifc_validator" in results and "error" not in results["ifc_validator"]:
        print("✅ IFC Validator: 検証完了")
    elif "ifc_validator" in results:
        print("❌ IFC Validator: エラーあり")

    if "ifcopenshell" in results and "error" not in results["ifcopenshell"]:
        print("✅ ifcopenshell: 基本検証OK")
    elif "ifcopenshell" in results:
        print("❌ ifcopenshell: エラーあり")

    print("\n💡 推奨事項:")
    print("1. 結果ファイルで詳細なエラー・警告を確認してください")
    print(
        "2. BIMVisionで表示されない場合は、ファイルパスを英数字のみに変更してお試しください"
    )
    print("3. 大きなファイルの場合は、BIMVisionの読み込み設定を調整してください")


if __name__ == "__main__":
    main()
