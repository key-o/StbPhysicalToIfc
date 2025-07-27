# StbPhysicalToIfc - EXEファイル作成ガイド

このドキュメントでは、PyInstallerを使用してStbPhysicalToIfcプロジェクトから実行可能ファイル（.exe）を作成する方法について説明します。

## 前提条件

- Python 3.10以上がインストールされていること
- プロジェクトの依存関係がインストールされていること
- PyInstallerがインストールされていること

## 1. 環境準備

### 1.1 PyInstallerのインストール

```cmd
pip install pyinstaller
```

または、requirements.txtに既に含まれているため：

```cmd
pip install -r requirements.txt
```

### 1.2 依存関係の確認

プロジェクトの主要な依存関係：

- ifcopenshell >= 0.8.0
- Python標準ライブラリ（tkinter, xml, json, math, uuid等）

## 2. EXEファイルの作成

### 2.1 基本的なEXEファイル作成

```cmd
pyinstaller --onefile main.py
```

### 2.2 推奨設定でのEXEファイル作成

```cmd
pyinstaller --onefile --windowed --name "StbPhysicalToIfc" --icon icon.ico main.py
```

#### オプションの説明

- `--onefile`: 単一の実行ファイルとして作成
- `--windowed`: コンソールウィンドウを表示しない（GUIアプリケーション用）
- `--name "StbPhysicalToIfc"`: 実行ファイル名を指定
- `--icon icon.ico`: アイコンファイルを指定

### 2.3 詳細設定でのEXEファイル作成（推奨）

```cmd
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "StbPhysicalToIfc" ^
  --icon icon.ico ^
  --add-data "materials;materials" ^
  --add-data "sampleStb;sampleStb" ^
  --hidden-import=ifcopenshell ^
  --hidden-import=tkinter ^
  --hidden-import=xml.etree.ElementTree ^
  --hidden-import=ui ^
  --hidden-import=ui.cli_interface ^
  --hidden-import=common ^
  --hidden-import=common.concrete_strength_utils ^
  --hidden-import=common.definition_processor ^
  --hidden-import=common.extractor_utils ^
  --hidden-import=common.geometry ^
  --hidden-import=common.guid_utils ^
  --hidden-import=common.json_utils ^
  --hidden-import=common.profile_naming_standards ^
  --hidden-import=common.xml_parser_cache ^
  --hidden-import=common.xml_utils ^
  --hidden-import=core ^
  --hidden-import=core.conversion_api ^
  --hidden-import=core.conversion_orchestrator ^
  --hidden-import=core.conversion_service ^
  --hidden-import=core.default_story_service ^
  --hidden-import=core.element_centric_converter ^
  --hidden-import=core.element_centric_integration_service ^
  --hidden-import=core.element_counter ^
  --hidden-import=core.element_output_service ^
  --hidden-import=core.element_parsing_service ^
  --hidden-import=core.element_story_analyzer ^
  --hidden-import=core.ifc_generation_service ^
  --hidden-import=core.service_container ^
  --hidden-import=core.stb_file_service ^
  --hidden-import=core.story_element_relationship_manager ^
  --hidden-import=ifcCreator ^
  --hidden-import=ifcCreator.api ^
  --hidden-import=ifcCreator.core ^
  --hidden-import=ifcCreator.core.element_creation_factory ^
  --hidden-import=ifcCreator.core.ifc_project_builder ^
  --hidden-import=ifcCreator.core.story_converter ^
  --hidden-import=ifcCreator.creators ^
  --hidden-import=ifcCreator.creators.base_creator ^
  --hidden-import=ifcCreator.creators.beam_creator ^
  --hidden-import=ifcCreator.creators.brace_creator ^
  --hidden-import=ifcCreator.creators.column_creator ^
  --hidden-import=ifcCreator.creators.material_creator ^
  --hidden-import=ifcCreator.creators.slab_creator ^
  --hidden-import=ifcCreator.creators.type_creator ^
  --hidden-import=ifcCreator.creators.wall_creator ^
  --hidden-import=ifcCreator.geometry ^
  --hidden-import=ifcCreator.geometry.geometry_builder ^
  --hidden-import=ifcCreator.geometry.structural_geometry ^
  --hidden-import=ifcCreator.services ^
  --hidden-import=ifcCreator.services.geometry_service ^
  --hidden-import=ifcCreator.services.profile_service ^
  --hidden-import=ifcCreator.services.property_service ^
  --hidden-import=ifcCreator.services.type_service ^
  --hidden-import=ifcCreator.specialized ^
  --hidden-import=ifcCreator.specialized.footing_creator ^
  --hidden-import=ifcCreator.specialized.foundation_column_creator ^
  --hidden-import=ifcCreator.specialized.foundation_element_creator ^
  --hidden-import=ifcCreator.specialized.grid_creator ^
  --hidden-import=ifcCreator.specialized.parapet_creator ^
  --hidden-import=ifcCreator.specialized.pile_creator ^
  --hidden-import=ifcCreator.specialized.strip_footing_creator ^
  --hidden-import=ifcCreator.specialized.wall_opening_service ^
  --hidden-import=ifcCreator.utils ^
  --hidden-import=ifcCreator.utils.definition_processor ^
  --hidden-import=ifcCreator.utils.structural_section ^
  --hidden-import=ifcCreator.utils.validator ^
  --hidden-import=stbParser ^
  --hidden-import=utils ^
  --hidden-import=stbParser.axes_extractor ^
  --hidden-import=stbParser.base_extractor ^
  --hidden-import=stbParser.beam_extractor ^
  --hidden-import=stbParser.beam_section_extractor ^
  --hidden-import=stbParser.brace_extractor ^
  --hidden-import=stbParser.brace_section_extractor ^
  --hidden-import=stbParser.column_extractor ^
  --hidden-import=stbParser.column_section_extractor ^
  --hidden-import=stbParser.footing_extractor ^
  --hidden-import=stbParser.footing_section_extractor ^
  --hidden-import=stbParser.foundation_column_extractor ^
  --hidden-import=stbParser.node_extractor ^
  --hidden-import=stbParser.pile_extractor ^
  --hidden-import=stbParser.pile_section_extractor ^
  --hidden-import=stbParser.section_extractor ^
  --hidden-import=stbParser.section_extractor_base ^
  --hidden-import=stbParser.slab_extractor ^
  --hidden-import=stbParser.slab_section_extractor ^
  --hidden-import=stbParser.src_section_extractor ^
  --hidden-import=stbParser.unified_section_processor ^
  --hidden-import=stbParser.unified_stb_parser ^
  --hidden-import=stbParser.wall_extractor ^
  --hidden-import=stbParser.wall_section_extractor ^
  --hidden-import=stbParser.xml_parser ^
  --paths=. ^
  --exclude-module=pytest ^
  --exclude-module=mypy ^
  --exclude-module=flake8 ^
  --exclude-module=psutil ^
  main.py
```

#### 追加オプションの説明

- `--add-data`: 追加データファイル/フォルダを含める
- `--hidden-import`: 明示的にインポートするモジュールを指定
- `--paths=.`: 現在のディレクトリをパッケージ検索パスに追加
- `--exclude-module`: 不要なモジュールを除外してファイルサイズを削減
- `--windowed`: コンソールウィンドウを非表示にする（GUIアプリケーション用）

**重要**: `ui`、`common`、`core`、`ifcCreator`、`stbParser`などのローカルモジュールは`--hidden-import`で明示的に指定する必要があります。

## 3. 高度な設定（.specファイルを使用）

### 3.1 specファイルの生成

```cmd
pyinstaller --onefile --name "StbPhysicalToIfc" main.py
```

これにより `StbPhysicalToIfc.spec` ファイルが生成されます。

### 3.2 specファイルのカスタマイズ

生成された `StbPhysicalToIfc.spec` ファイルを編集して、より詳細な設定を行います：

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('materials', 'materials'),
        ('sampleStb', 'sampleStb'),
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'ifcopenshell',
        'tkinter',
        'xml.etree.ElementTree',
        'ui',
        'ui.cli_interface',
        'common',
        'common.concrete_strength_utils',
        'common.definition_processor',
        'common.extractor_utils',
        'common.geometry',
        'common.guid_utils',
        'common.json_utils',
        'common.profile_naming_standards',
        'common.xml_parser_cache',
        'common.xml_utils',
        'core',
        'core.conversion_api',
        'core.conversion_orchestrator',
        'core.conversion_service',
        'core.default_story_service',
        'core.element_centric_converter',
        'core.element_centric_integration_service',
        'core.element_counter',
        'core.element_output_service',
        'core.element_parsing_service',
        'core.element_story_analyzer',
        'core.ifc_generation_service',
        'core.service_container',
        'core.stb_file_service',
        'core.story_element_relationship_manager',
        'ifcCreator',
        'ifcCreator.api',
        'ifcCreator.core',
        'ifcCreator.core.element_creation_factory',
        'ifcCreator.core.ifc_project_builder',
        'ifcCreator.core.story_converter',
        'ifcCreator.creators',
        'ifcCreator.creators.base_creator',
        'ifcCreator.creators.beam_creator',
        'ifcCreator.creators.brace_creator',
        'ifcCreator.creators.column_creator',
        'ifcCreator.creators.material_creator',
        'ifcCreator.creators.slab_creator',
        'ifcCreator.creators.type_creator',
        'ifcCreator.creators.wall_creator',
        'ifcCreator.geometry',
        'ifcCreator.geometry.geometry_builder',
        'ifcCreator.geometry.structural_geometry',
        'ifcCreator.services',
        'ifcCreator.services.geometry_service',
        'ifcCreator.services.profile_service',
        'ifcCreator.services.property_service',
        'ifcCreator.services.type_service',
        'ifcCreator.specialized',
        'ifcCreator.specialized.footing_creator',
        'ifcCreator.specialized.foundation_column_creator',
        'ifcCreator.specialized.foundation_element_creator',
        'ifcCreator.specialized.grid_creator',
        'ifcCreator.specialized.parapet_creator',
        'ifcCreator.specialized.pile_creator',
        'ifcCreator.specialized.strip_footing_creator',
        'ifcCreator.specialized.wall_opening_service',
        'ifcCreator.utils',
        'ifcCreator.utils.definition_processor',
        'ifcCreator.utils.structural_section',
        'ifcCreator.utils.validator',
        'stbParser',
        'stbParser.axes_extractor',
        'stbParser.base_extractor',
        'stbParser.beam_extractor',
        'stbParser.beam_section_extractor',
        'stbParser.brace_extractor',
        'stbParser.brace_section_extractor',
        'stbParser.column_extractor',
        'stbParser.column_section_extractor',
        'stbParser.footing_extractor',
        'stbParser.footing_section_extractor',
        'stbParser.foundation_column_extractor',
        'stbParser.node_extractor',
        'stbParser.pile_extractor',
        'stbParser.pile_section_extractor',
        'stbParser.section_extractor',
        'stbParser.section_extractor_base',
        'stbParser.slab_extractor',
        'stbParser.slab_section_extractor',
        'stbParser.src_section_extractor',
        'stbParser.unified_section_processor',
        'stbParser.unified_stb_parser',
        'stbParser.wall_extractor',
        'stbParser.wall_section_extractor',
        'stbParser.xml_parser',
        'utils',
        'utils.logger',
        'utils',
        'config',
        'config.element_centric_config',
        'config.settings',
        'exceptions',
        'exceptions.custom_errors',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'mypy',
        'flake8', 
        'black',
        'psutil',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StbPhysicalToIfc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
```

### 3.3 specファイルからのビルド

```cmd
pyinstaller StbPhysicalToIfc.spec
```

## 4. ビルド後の確認

### 4.1 出力ファイルの場所

ビルドが完了すると、以下の場所にファイルが生成されます：

- `dist/StbPhysicalToIfc.exe` - 実行可能ファイル
- `build/` - 一時ビルドファイル

### 4.2 動作確認

1. `dist/StbPhysicalToIfc.exe` をダブルクリックして起動
2. GUIが正常に表示されることを確認
3. サンプルSTBファイルでの変換テストを実行

## 5. トラブルシューティング

### 5.1 よくある問題と解決方法

#### モジュールが見つからないエラー

```text
ModuleNotFoundError: No module named 'xxx'
```

**解決方法**: `--hidden-import=xxx` オプションを追加

#### ローカルモジュール（ui、common、core等）が見つからないエラー

```text
ModuleNotFoundError: No module named 'ui'
```

**解決方法**:

1. `--hidden-import=ui` オプションを追加
2. `--paths=.` オプションを追加してカレントディレクトリをパスに含める
3. specファイルを使用している場合は、`pathex=['.']` を設定

#### tkinterエラー

```text
ImportError: No module named '_tkinter'
```

**解決方法**: Pythonがtkinterサポート付きでインストールされていることを確認

#### ifcopenshellエラー

```text
ImportError: No module named 'ifcopenshell'
```

**解決方法**: `--hidden-import=ifcopenshell` を明示的に追加

#### 文字エンコーディングエラー

```text
UnicodeEncodeError: 'cp932' codec can't encode character '\u2705' in position 0: illegal multibyte sequence
```

**解決方法**:

1. main.pyで文字エンコーディングを適切に設定
2. 絵文字や特殊文字を避けるか、安全な文字に置換
3. コンソール出力時のエラーハンドリングを追加

このプロジェクトでは既に対策済みです。

#### PyInstaller windowedモードでの標準出力エラー

```text
AttributeError: 'NoneType' object has no attribute 'reconfigure'
AttributeError: 'NoneType' object has no attribute 'buffer'
```

**原因**: `--windowed`オプションでEXEを作成した場合、標準出力・標準エラー出力が`None`になります。

**解決方法**:

1. 標準出力の存在確認を追加
2. エラー情報をログファイルに出力
3. 安全なprint関数を使用

このプロジェクトでは既に対策済みです。デバッグが必要な場合は`build_exe_debug.bat`（コンソールあり）を使用してください。

### 5.2 ファイルサイズの最適化

大きなEXEファイルを小さくする方法：

```cmd
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "Stb2IFC" ^
  --icon icon.ico ^
  --exclude-module=pytest ^
  --exclude-module=unittest ^
  --exclude-module=pdb ^
  --exclude-module=doctest ^
  --upx-dir="C:\path\to\upx" ^
  main.py
```

### 5.3 デバッグオプション

問題が発生した場合のデバッグ用オプション：

```cmd
pyinstaller --onefile --console --debug=all main.py
```

## 6. ライセンス対応

### 6.1 必要なライセンスファイル

ifcopenshellがLGPL 3.0ライセンスのため、EXE配布時に以下が必要です：

1. **LGPLライセンス文書の同梱**
2. **著作権表示**
3. **使用ライブラリの明示**

### 6.2 ライセンスファイルの準備

配布パッケージに以下を含めてください：

```
Stb2IFC_v1.0/
├── Stb2IFC.exe
├── LICENSE.txt              # あなたのプロジェクトのライセンス
├── THIRD_PARTY_LICENSES.txt # 使用ライブラリのライセンス情報
├── README.txt
└── documentation/
```

### 6.3 THIRD_PARTY_LICENSES.txtの例

```text
This software uses the following third-party libraries:

ifcopenshell-python
License: GNU Lesser General Public License v3.0 (LGPL-3.0)
Copyright: IfcOpenShell contributors
Website: https://github.com/IfcOpenShell/IfcOpenShell
License text: See full LGPL-3.0 license at https://www.gnu.org/licenses/lgpl-3.0.html

[その他の使用ライブラリ...]
```

### 6.4 アプリケーション内での表示

main.pyまたはGUIに以下のような表示を追加することをお勧めします：

```python
def show_about():
    about_text = """
Stb2IFC Converter
Copyright (c) 2024 [Your Name]

This software uses ifcopenshell-python library.
ifcopenshell is licensed under LGPL-3.0.
See THIRD_PARTY_LICENSES.txt for details.
"""
    # GUIダイアログまたはコンソール出力
```

## 7. 高度な設定（.specファイルを使用）

## 8. EXE実行時のユーザー体験向上

### 8.1 変換完了メッセージ

PyInstallerの`--windowed`オプションでEXE化した場合、コンソールウィンドウが表示されないため、以下の機能を実装しています：

1. **変換完了時のメッセージボックス表示**
   - 変換が正常に完了した際に、結果を表示するダイアログが自動的に表示されます
   - 入力ファイル名と出力ファイル名が確認できます

2. **エラー時のメッセージボックス表示**
   - 変換中にエラーが発生した場合、詳細なエラー情報がダイアログで表示されます
   - エラーログファイルの場所も案内されます

3. **設定による制御**
   - `config/settings.py`でメッセージボックスの表示を制御できます

   ```python
   show_completion_dialog: bool = True  # 完了ダイアログの表示
   show_error_dialog: bool = True       # エラーダイアログの表示
   ```

### 8.2 デバッグ版との使い分け

- **本番版EXE** (`build_exe.bat`):
  - ウィンドウモード、メッセージボックス表示あり
  - 一般ユーザー向け

- **デバッグ版EXE** (`build_exe_debug.bat`):
  - コンソールモード、詳細ログ表示
  - 開発者・トラブルシューティング向け

## 9. 配布用パッケージの作成

### 8.1 基本パッケージ構成

```
Stb2IFC_v1.0/
├── Stb2IFC.exe
├── README.txt
├── sample_files/
│   └── （サンプルSTBファイル）
└── documentation/
    └── （ユーザーマニュアル）
```

### 6.2 バッチファイルでの自動ビルド

`build_exe.bat` ファイルを作成：

```batch
@echo off
chcp 65001 > nul
echo Stb2IFC EXE ビルドを開始します...

echo.
echo 1. 依存関係をインストール中...
pip install -r requirements.txt

echo.
echo 2. 既存のビルドファイルをクリア中...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Stb2IFC.spec del Stb2IFC.spec

echo.
echo 3. EXEファイルをビルド中...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "Stb2IFC" ^
  --icon icon.ico ^
  --add-data "materials;materials" ^
  --add-data "sampleStb;sampleStb" ^
  --hidden-import=ifcopenshell ^
  --hidden-import=tkinter ^
  --hidden-import=ui ^
  --hidden-import=ui.cli_interface ^
  --hidden-import=common ^
  --hidden-import=core ^
  --hidden-import=ifcCreator ^
  --hidden-import=stbParser ^
  --hidden-import=utils ^
  --paths=. ^
  --exclude-module=pytest ^
  main.py

echo.
echo 4. ビルド完了確認...
if exist dist\Stb2IFC.exe (
    echo ✅ ビルドが正常に完了しました！
    echo 📁 実行ファイル: dist\Stb2IFC.exe
) else (
    echo ❌ ビルドに失敗しました
    exit /b 1
)

echo.
echo 5. ファイルサイズ確認...
for %%A in (dist\Stb2IFC.exe) do echo ファイルサイズ: %%~zA bytes

pause
```

## 7. GitHub Actions での自動ビルド（オプション）

`.github/workflows/build-exe.yml` ファイルを作成して、GitHub Actionsでの自動ビルドも可能です：

```yaml
name: Build EXE

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build EXE
      run: |
        pyinstaller --onefile --windowed --name "Stb2IFC" --icon icon.ico main.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: Stb2IFC-exe
        path: dist/Stb2IFC.exe
```

## 8. クイックスタート

このプロジェクトには、EXEファイルを簡単にビルドできるバッチファイルが含まれています：

### 8.1 本番用EXEファイルの作成

```cmd
build_exe.bat
```

このバッチファイルを実行すると：

- 依存関係の自動インストール
- 既存ビルドファイルのクリアップ
- 最適化されたEXEファイルの作成
- ビルド結果の確認
- 動作テスト（オプション）

### 8.2 デバッグ用EXEファイルの作成

問題が発生した場合は、デバッグ版を作成してエラー詳細を確認できます：

```cmd
build_exe_debug.bat
```

デバッグ版では：

- コンソールウィンドウが表示される
- 詳細なエラーログが出力される
- 問題の特定が容易になる

### 8.3 推奨ワークフロー

1. **最初に**: `build_exe_debug.bat` でデバッグ版を作成し、正常に動作することを確認
2. **問題がなければ**: `build_exe.bat` で本番用EXEファイルを作成
3. **問題があれば**: デバッグ版のログを確認し、必要に応じて`--hidden-import`オプションを追加

## まとめ

このガイドに従って、Stb2IFCプロジェクトから実行可能なEXEファイルを作成できます。基本的な用途には簡単なコマンドで十分ですが、より詳細な制御が必要な場合は、specファイルを使用したカスタマイズを検討してください。

**最も簡単な方法**: プロジェクトルートで `build_exe.bat` を実行するだけです！
