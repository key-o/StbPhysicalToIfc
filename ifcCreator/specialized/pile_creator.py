"""IFC杭作成クラス"""

import ifcopenshell
from ..creators.column_creator import ColumnCreator as IFCColumnCreator
from ..utils.structural_section import StructuralSection
from common.geometry import Point3D


class IFCPileCreator(IFCColumnCreator):
    """IfcPile オブジェクトを生成するクリエータ"""

    def create_project_structure(
        self,
        project_name: str = "杭プロジェクト",
    ) -> "ifcopenshell.file":
        return super().create_project_structure(project_name)

    def create_piles(self, pile_defs: list) -> list:
        """杭要素の一括作成
        
        Args:
            pile_defs: 杭定義のリスト
            
        Returns:
            作成された杭要素のリスト
        """
        piles = []
        
        for i, pile_def in enumerate(pile_defs):
            try:
                # 杭定義を処理
                processed_def = self.process_pile_definition(pile_def, i)
                
                # 必要なパラメータを取得
                bottom_point = processed_def.get('bottom_point')
                top_point = processed_def.get('top_point')
                section = processed_def.get('section')
                pile_name = processed_def.get('name', f'Pile_{i+1}')
                pile_tag = processed_def.get('tag', f'P{i+1:03d}')
                stb_guid = processed_def.get('stb_guid')
                
                if bottom_point and top_point and section:
                    pile = self.create_pile(
                        bottom_point=bottom_point,
                        top_point=top_point,
                        section=section,
                        pile_name=pile_name,
                        pile_tag=pile_tag,
                        stb_guid=stb_guid
                    )
                    piles.append(pile)
                    self.logger.info(f"杭作成成功: {pile_name}")
                else:
                    self.logger.warning(f"杭定義不完全 (index {i}): 必要パラメータが不足")
                    
            except Exception as e:
                self.logger.error(f"杭作成失敗 (index {i}): {e}")
                
        self.logger.info(f"杭一括作成完了: {len(piles)}個作成")
        return piles

    def create_pile(
        self,
        bottom_point: Point3D,
        top_point: Point3D,
        section: StructuralSection,
        pile_name: str = "Pile",
        pile_tag: str = "P001",
        rotation_radians: float = 0.0,
        stb_guid: str | None = None,
    ):
        """杭要素を作成"""
        if not self.project_builder or not self.project_builder.file:
            self.logger.warning("プロジェクトビルダーまたはIFCファイルが設定されていません")
            return None

        try:
            # 杭の幾何形状を計算（柱と同様の計算を使用）
            height = abs(top_point.z - bottom_point.z)
            if height <= 0:
                self.logger.error(f"杭 '{pile_name}' の高さが無効です: {height}")
                return None

            # 配置の作成
            placement = self.project_builder.file.createIfcLocalPlacement(
                None,
                self.project_builder.file.createIfcAxis2Placement3D(
                    self.project_builder.file.createIfcCartesianPoint([bottom_point.x, bottom_point.y, bottom_point.z]),
                    self.project_builder.file.createIfcDirection([0., 0., 1.]),
                    self.project_builder.file.createIfcDirection([1., 0., 0.])
                )
            )

            # sectionが辞書の場合とStructuralSectionオブジェクトの場合を両方サポートするヘルパー関数
            def get_section_property(key: str, default=None):
                if hasattr(section, 'properties'):
                    return section.properties.get(key, default)
                elif isinstance(section, dict):
                    return section.get(key, default)
                else:
                    return getattr(section, key, default)

            # デバッグ: sectionデータの内容を確認
            print(f"DEBUG: Pile section data = {section}")
            print(f"DEBUG: Section type = {type(section)}")

            # プロファイル作成（円形の場合）
            # STB抽出キー(radius, outer_diameter, diameter)に対応
            radius = get_section_property('radius')
            print(f"DEBUG: Extracted radius = {radius}")
            if radius is None:
                outer_diameter = get_section_property('outer_diameter')
                if outer_diameter is not None:
                    radius = outer_diameter / 2.0
                else:
                    diameter = get_section_property('diameter')
                    if diameter is not None:
                        radius = diameter / 2.0
                    else:
                        radius = 250.0  # デフォルト値
            
            profile = self.project_builder.file.createIfcCircleProfileDef(
                "AREA", f"PileProfile_{radius*2}", None, radius
            )

            # 押し出し形状の作成
            direction = self.project_builder.file.createIfcDirection([0., 0., 1.])
            shape = self.project_builder.file.createIfcExtrudedAreaSolid(
                profile, None, direction, height
            )

            # 形状表現の作成（3Dコンテキストを使用）
            shape_representation = self.project_builder.file.createIfcShapeRepresentation(
                self.project_builder.get_3d_context(),
                "Body", "SweptSolid", [shape]
            )

            # 製品定義形状の作成
            product_definition_shape = self.project_builder.file.createIfcProductDefinitionShape(
                None, None, [shape_representation]
            )

            # GUIDを生成または変換
            from common.guid_utils import convert_stb_guid_to_ifc, create_ifc_guid

            try:
                if stb_guid:
                    element_guid = convert_stb_guid_to_ifc(stb_guid)
                else:
                    element_guid = create_ifc_guid()
            except Exception:
                element_guid = create_ifc_guid()

            # 杭要素の作成
            pile = self.project_builder.file.createIfcPile(
                element_guid,
                self.project_builder.owner_history,
                pile_name,
                f"Description for {pile_name}",
                pile_tag,
                placement,
                product_definition_shape,
                "NOTDEFINED",
                "NOTDEFINED"
            )

            # 杭作成完了をデバッグログに記録
            self.logger.debug(f"杭を作成しました: 名前={pile_name}, GUID={element_guid}")

            # 空間構造に追加
            if hasattr(self.project_builder, 'add_element_to_spatial_structure'):
                self.project_builder.add_element_to_spatial_structure(pile)

            return pile

        except Exception as e:
            self.logger.error(f"杭作成エラー ({pile_name}): {e}")
            return None

    @staticmethod
    def process_pile_definition(pdef: dict, index: int) -> dict:
        """杭定義を処理

        Args:
            pdef: 杭定義辞書
            index: インデックス（ログ用）

        Returns:
            処理済み定義辞書

        Raises:
            ValueError: 必要なパラメータが不足している場合
        """
        from ..utils.structural_section import StructuralSection
        from common.definition_processor import DefinitionProcessor

        processed = DefinitionProcessor.process_vertical_element_definition(
            pdef, index, "杭", StructuralSection
        )
        # 杭は統一断面なので、sec_bottomをsectionとしても設定
        if "sec_bottom" in processed:
            processed["section"] = processed["sec_bottom"]
        return processed
