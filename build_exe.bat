@echo off
chcp 65001 > nul
echo Stb2Ifc EXE ビルドを開始します...

echo.
echo 1. 依存関係をインストール中...
pip install -r requirements.txt

echo.
echo 2. 既存のビルドファイルをクリア中...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Stb2Ifc.spec del Stb2Ifc.spec

echo.
echo 3. EXEファイルをビルド中...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "Stb2Ifc" ^
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
  --hidden-import=utils ^
  --hidden-import=utils.logger ^
  --hidden-import=config ^
  --hidden-import=config.element_centric_config ^
  --hidden-import=config.settings ^
  --hidden-import=exceptions ^
  --hidden-import=exceptions.custom_errors ^
  --paths=. ^
  --exclude-module=pytest ^
  --exclude-module=mypy ^
  --exclude-module=flake8 ^
  --exclude-module=black ^
  --exclude-module=psutil ^
  main.py

echo.
echo 4. ビルド完了確認...
if exist dist\Stb2Ifc.exe (
    echo [OK] ビルドが正常に完了しました！
    echo 実行ファイル: dist\Stb2Ifc.exe
) else (
    echo [ERROR] ビルドに失敗しました
    echo 詳細なエラーログについては、上記のログを確認してください。
    echo.
    echo よくある解決方法:
    echo 1. すべての依存関係がインストールされていることを確認
    echo 2. Pythonが正しく設定されていることを確認
    echo 3. PyInstallerを最新に更新: pip install --upgrade pyinstaller
    exit /b 1
)

echo.
echo 5. ファイルサイズ確認...
for %%A in (dist\Stb2Ifc.exe) do echo ファイルサイズ: %%~zA bytes

echo.
echo 6. 動作テスト（オプション）...
echo EXEファイルの動作テストを実行しますか？ [Y/N]
set /p TEST_CHOICE=
if /i "%TEST_CHOICE%"=="Y" (
    echo テスト実行中...
    cd dist
    Stb2Ifc.exe --help
    cd ..
)

echo.
echo [OK] すべての処理が完了しました！
echo 作成されたファイル: dist\Stb2Ifc.exe
echo.
pause
