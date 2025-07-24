"""材料定義を作成するCreator"""

import uuid


class MaterialCreator:
    """IFC材料定義（Material、MaterialProfile等）を作成するクラス"""

    def __init__(self, ifc_file, owner_history):
        """
        Args:
            ifc_file: IfcOpenShellのファイルオブジェクト
            owner_history: IfcOwnerHistory
        """
        self.ifc_file = ifc_file
        self.owner_history = owner_history
        self._materials_cache = {}

    def create_material(self, name, description=None):
        """材料を作成

        Args:
            name: 材料名
            description: 材料の説明

        Returns:
            IfcMaterial: 作成された材料
        """
        if name in self._materials_cache:
            return self._materials_cache[name]

        material = self.ifc_file.create_entity(
            "IfcMaterial", Name=name, Description=description
        )

        self._materials_cache[name] = material
        return material

    def create_steel_material(self):
        """鋼材を作成"""
        return self.create_material("Steel", "Structural Steel")

    def create_concrete_material(self):
        """コンクリート材料を作成"""
        return self.create_material("Concrete", "Reinforced Concrete")

    def create_material_profile(self, material, profile, name=None):
        """材料プロファイルを作成

        Args:
            material: IfcMaterial
            profile: IfcProfileDef
            name: プロファイル名

        Returns:
            IfcMaterialProfile: 作成された材料プロファイル
        """
        return self.ifc_file.create_entity(
            "IfcMaterialProfile", Name=name, Material=material, Profile=profile
        )

    def create_material_profile_set(self, material_profiles, name=None):
        """材料プロファイルセットを作成

        Args:
            material_profiles: IfcMaterialProfileのリスト
            name: セット名

        Returns:
            IfcMaterialProfileSet: 作成された材料プロファイルセット
        """
        if not isinstance(material_profiles, list):
            material_profiles = [material_profiles]

        return self.ifc_file.create_entity(
            "IfcMaterialProfileSet", Name=name, MaterialProfiles=material_profiles
        )

    def associate_material_to_elements(self, elements, material):
        """材料を要素に関連付け

        Args:
            elements: 要素リスト（単一要素も可）
            material: IfcMaterial または IfcMaterialProfileSet

        Returns:
            IfcRelAssociatesMaterial: 作成された関係
        """
        if not isinstance(elements, list):
            elements = [elements]

        return self.ifc_file.create_entity(
            "IfcRelAssociatesMaterial",
            GlobalId=str(uuid.uuid4()),
            OwnerHistory=self.owner_history,
            RelatedObjects=elements,
            RelatingMaterial=material,
        )

    def get_material_for_profile(self, profile_name):
        """プロファイル名に基づいて適切な材料を取得"""
        if any(
            keyword in profile_name.upper() for keyword in ["H", "I", "BOX", "HOLLOW"]
        ):
            return self.create_steel_material()
        elif "RECT" in profile_name.upper():
            return self.create_concrete_material()
        else:
            return self.create_steel_material()  # デフォルトは鋼材

    def create_material_for_element_type(self, element_type, profile_name=None):
        """要素タイプに基づいて材料を作成・取得

        Args:
            element_type: "beam", "column", "slab", "footing"
            profile_name: プロファイル名（オプション）

        Returns:
            IfcMaterial: 適切な材料
        """
        if element_type.lower() in ["slab", "footing"]:
            return self.create_concrete_material()
        elif profile_name:
            return self.get_material_for_profile(profile_name)
        else:
            return self.create_steel_material()  # デフォルト
