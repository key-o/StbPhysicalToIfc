"""型定義（Type）を作成するCreator"""

import uuid


class TypeCreator:
    """IFC型定義（BeamType、ColumnType等）を作成するクラス"""

    def __init__(self, ifc_file, owner_history):
        """
        Args:
            ifc_file: IfcOpenShellのファイルオブジェクト
            owner_history: IfcOwnerHistory
        """
        self.ifc_file = ifc_file
        self.owner_history = owner_history
        self._types_cache = {}

    def create_beam_type(self, type_name="StandardBeam"):
        """梁タイプを作成

        Args:
            type_name: タイプ名

        Returns:
            IfcBeamType: 作成された梁タイプ
        """
        if type_name in self._types_cache:
            return self._types_cache[type_name]

        beam_type = self.ifc_file.create_entity(
            "IfcBeamType",
            GlobalId=str(uuid.uuid4()),
            OwnerHistory=self.owner_history,
            Name=type_name,
            ElementType="BEAM",
        )

        self._types_cache[type_name] = beam_type
        return beam_type

    def create_column_type(self, type_name="StandardColumn"):
        """柱タイプを作成

        Args:
            type_name: タイプ名

        Returns:
            IfcColumnType: 作成された柱タイプ
        """
        if type_name in self._types_cache:
            return self._types_cache[type_name]

        column_type = self.ifc_file.create_entity(
            "IfcColumnType",
            GlobalId=str(uuid.uuid4()),
            OwnerHistory=self.owner_history,
            Name=type_name,
            ElementType="COLUMN",
        )

        self._types_cache[type_name] = column_type
        return column_type

    def create_slab_type(self, type_name="StandardSlab"):
        """スラブタイプを作成

        Args:
            type_name: タイプ名

        Returns:
            IfcSlabType: 作成されたスラブタイプ
        """
        if type_name in self._types_cache:
            return self._types_cache[type_name]

        slab_type = self.ifc_file.create_entity(
            "IfcSlabType",
            GlobalId=str(uuid.uuid4()),
            OwnerHistory=self.owner_history,
            Name=type_name,
            ElementType="FLOOR",
        )

        self._types_cache[type_name] = slab_type
        return slab_type

    def create_footing_type(self, type_name="StandardFooting"):
        """基礎タイプを作成

        Args:
            type_name: タイプ名

        Returns:
            IfcFootingType: 作成された基礎タイプ
        """
        if type_name in self._types_cache:
            return self._types_cache[type_name]

        footing_type = self.ifc_file.create_entity(
            "IfcFootingType",
            GlobalId=str(uuid.uuid4()),
            OwnerHistory=self.owner_history,
            Name=type_name,
            ElementType="FOOTING",
        )

        self._types_cache[type_name] = footing_type
        return footing_type

    def relate_element_to_type(self, elements, element_type):
        """要素を型に関連付け

        Args:
            elements: 要素リスト（単一要素も可）
            element_type: 型定義

        Returns:
            IfcRelDefinesByType: 作成された関係
        """
        if not isinstance(elements, list):
            elements = [elements]

        return self.ifc_file.create_entity(
            "IfcRelDefinesByType",
            GlobalId=str(uuid.uuid4()),
            OwnerHistory=self.owner_history,
            RelatedObjects=elements,
            RelatingType=element_type,
        )

    def get_beam_type_for_profile(self, profile_name):
        """プロファイル名に基づいて適切な梁タイプを取得"""
        if "H" in profile_name or "I" in profile_name:
            return self.create_beam_type("SteelBeam")
        elif "RECT" in profile_name:
            return self.create_beam_type("ConcreteBeam")
        else:
            return self.create_beam_type("StandardBeam")

    def get_column_type_for_profile(self, profile_name):
        """プロファイル名に基づいて適切な柱タイプを取得"""
        if "H" in profile_name or "I" in profile_name:
            return self.create_column_type("SteelColumn")
        elif "BOX" in profile_name:
            return self.create_column_type("CFTColumn")
        elif "RECT" in profile_name:
            return self.create_column_type("ConcreteColumn")
        else:
            return self.create_column_type("StandardColumn")
