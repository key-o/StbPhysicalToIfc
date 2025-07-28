# STB ファイルを IFC に変換するツール

## 📋 概要

STB (ST-Bridge) から IFC (Industry Foundation Classes) への変換を行うPython製ツールです。
ST-BridgeのジオメトリのみをIFC要素に変換します。

**対応要素**: 梁・柱・ブレース・杭・スラブ・壁・フーチング・基礎柱・階層

## 🚀 クイックスタート

### インストール

```bash
# 依存関係をインストール
pip install -r requirements.txt
```

### 基本的な使用方法

```bash
# 🚀 最もシンプル：ファイル選択ダイアログが自動で開きます
python3.11 main.py

# ファイルを指定して変換
python3.11 main.py input.stb

# 出力ファイル名を指定
python3.11 main.py input.stb -o output.ifc

# 💡 明示的にファイル選択ダイアログを使用
python3.11 main.py --select-file

# 変換情報のみ表示（変換は行わない）
python3.11 main.py --info input.stb

# デバッグモードで実行
python3.11 main.py input.stb --debug
```

**または専用CLIを使用:**

```bash
python3.11 stb2ifc_cli.py input.stb  # 専用CLI（上級者向け）
```

## 📂 ファイル選択方法

新しいバージョンでは、以下の方法でファイルを選択できます：

### 1. **最もシンプル（推奨）**

```bash
python3.11 main.py
```

- 🚀 **引数なしで実行するだけ！**
- GUI環境では tkinter ファイルダイアログが開きます
- CLI環境では自動的にデフォルトファイルを選択

### 2. **ファイルパス直接指定**

```bash
python3.11 main.py "path/to/your/file.stb"
```

### 3. **明示的なファイル選択ダイアログ**

```bash
python3.11 main.py --select-file
```

- GUI環境で tkinter ファイルダイアログが開きます
- `sampleStb/` ディレクトリから開始されます

### ファイル形式

- **入力**: STB v2.0.2 (XML)
- **出力**: IFC4 (STEP-File)

## ⚙️ 要件

### 必須要件

- **Python**: 3.11推奨 (IfcOpenShell互換性)
- **IfcOpenShell**: 0.8.x

### 追加ライブラリ

詳細は `requirements.txt` を参照

### GUI機能 (オプション)

ファイル選択ダイアログを使用する場合：

- **tkinter**: Python標準（通常は自動インストール）


#### 3. ファイルエンコーディングエラー

- STBファイルはUTF-8エンコーディングで保存してください
- Shift_JISの場合は自動検出・変換されます


## 🆕 バージョン履歴

### V2.2.0 (2025年7月24日)

---
