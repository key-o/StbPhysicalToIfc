# ライセンス遵守ガイド - ifcopenshell使用時の注意事項

## 概要

Stb2IFCプロジェクトはifcopenshell-pythonライブラリを使用しており、これはLGPL 3.0ライセンスの下で提供されています。EXE配布時にはライセンス要件を満たす必要があります。

## LGPL 3.0とOneFileEXE化

### ✅ 許可されること

- PyInstallerでの単一実行ファイル（--onefile）作成
- 商用・非商用問わず配布
- あなたのアプリケーションコードの独自ライセンス適用

### ⚠️ 必要な対応

1. **ライセンス文書の同梱**
2. **著作権表示**
3. **使用ライブラリの明示**

## 推奨する配布パッケージ構成

```
Stb2IFC_Release/
├── Stb2IFC.exe                 # メインプログラム
├── README.txt                  # 使用方法
├── THIRD_PARTY_LICENSES.txt    # サードパーティライセンス（必須）
├── LICENSE.txt                 # あなたのプロジェクトのライセンス
└── sample_files/               # サンプルファイル（オプション）
```

## THIRD_PARTY_LICENSES.txtの内容

以下の内容を含めてください：

```text
This software uses the following third-party libraries:

ifcopenshell-python
License: GNU Lesser General Public License v3.0 (LGPL-3.0)
Copyright: IfcOpenShell contributors
Website: https://github.com/IfcOpenShell/IfcOpenShell
License text: https://www.gnu.org/licenses/lgpl-3.0.html

Description: 
ifcopenshell-python is an open source software library for working with 
Industry Foundation Classes (IFC) files. It provides parsing support for 
IFC2x3, IFC4, IFC4x1, IFC4x2, and IFC4x3.
```

## アプリケーション内での表示

main.pyまたはUIに以下のような情報表示を追加することを推奨します：

```python
def show_about_dialog():
    about_text = """
Stb2IFC Converter
Version: 1.0.0
Copyright (c) 2024 [Your Name/Organization]

This software uses ifcopenshell-python library:
- License: LGPL-3.0
- Copyright: IfcOpenShell contributors
- Website: https://ifcopenshell.org/

For detailed license information, see THIRD_PARTY_LICENSES.txt
"""
    return about_text
```

## 自動生成されるファイル

`build_exe.bat`を実行すると、自動的に`THIRD_PARTY_LICENSES.txt`が生成されます。

## よくある質問

### Q: OneFileでの配布は本当に問題ないですか？

A: はい。LGPL 3.0はライブラリの使用を許可しており、適切なライセンス表示を行えば単一実行ファイルでの配布も可能です。

### Q: 商用利用は可能ですか？

A: はい。LGPLは商用利用を許可しています。ただし、ライセンス要件（クレジット表示など）は遵守する必要があります。

### Q: ソースコードの公開は必要ですか？

A: あなたのアプリケーションコードの公開は不要です。ただし、ifcopenshell自体のソースコードへのアクセス方法を明示する必要があります（通常はGitHubリンクで十分）。

## 参考資料

- [GNU LGPL 3.0 ライセンス](https://www.gnu.org/licenses/lgpl-3.0.html)
- [IfcOpenShell GitHub](https://github.com/IfcOpenShell/IfcOpenShell)
- [LGPL FAQ](https://www.gnu.org/licenses/gpl-faq.html)

## 更新履歴

- 2024-07-24: 初版作成
