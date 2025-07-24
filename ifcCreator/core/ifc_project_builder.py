# ifcCreator/ifc_project_builder.py
"""
共通IFCプロジェクト構造構築モジュール
梁・柱・その他構造要素で共通利用
Phase1強化: ServiceContainer統合
"""
import ifcopenshell
import uuid
import time
from typing import List, Optional
from common.guid_utils import create_ifc_guid


class IFCProjectBuilder:
    """IFCプロジェクト構造の構築責務（共通）

    Phase1強化: ServiceContainer統合による依存性注入
    """

    def __init__(
        self, application_name: str = "IFCStructuralCreator", service_container=None
    ):
        self.file = None
        self.owner_history = None
        self.model_context = None
        self.plan_context = None
        self.storey = None
        self.storey_placement = None
        self.building = None
        self.building_placement = None
        self.application_name = application_name

        # Phase1強化: ServiceContainer統合
        self.service_container = service_container
        if self.service_container is None:
            from core.service_container import get_global_container

            self.service_container = get_global_container()

    def create_project_structure(
        self, project_name: str = "構造プロジェクト"
    ) -> ifcopenshell.file:
        """IFCプロジェクト構造を作成

        Phase1強化: ServiceContainerとの連携
        """
        self.file = ifcopenshell.file(schema="IFC4")
        self._create_basic_structure(project_name)

        # Phase1強化: ServiceContainerにIFCファイルとモデルコンテキストを設定
        # Phase2強化: owner_historyも渡してMaterialCreatorを完全初期化
        if self.service_container:
            self.service_container.configure_services(self.file, self.model_context, None, self.owner_history)

        return self.file

    def _create_basic_structure(self, project_name: str):
        """基本的なプロジェクト構造を作成"""
        timestamp = int(time.time())

        def create_guid():
            return create_ifc_guid()

        # 人物・組織・アプリケーション情報
        person = self.file.createIfcPerson(GivenName="Taro", FamilyName="Yamada")
        org = self.file.createIfcOrganization(Name="SampleOrg")
        pao = self.file.createIfcPersonAndOrganization(
            ThePerson=person, TheOrganization=org
        )
        app = self.file.createIfcApplication(
            ApplicationDeveloper=org,
            Version="1.0",
            ApplicationFullName=self.application_name,
            ApplicationIdentifier="ifc_structural_creator",
        )

        self.owner_history = self.file.createIfcOwnerHistory(
            OwningUser=pao,
            OwningApplication=app,
            State="READWRITE",
            ChangeAction="ADDED",
            CreationDate=timestamp,
        )

        # 幾何学コンテキスト
        self._create_geometric_contexts()

        # 単位系
        units = self._create_units()
        unit_assign = self.file.createIfcUnitAssignment(Units=units)

        # プロジェクト
        context = self.file.createIfcGeometricRepresentationContext(
            ContextType="Model",
            CoordinateSpaceDimension=3,
            Precision=1e-5,
            WorldCoordinateSystem=self.file.createIfcAxis2Placement3D(
                Location=self.file.createIfcCartesianPoint([0.0, 0.0, 0.0])
            ),
        )

        project = self.file.createIfcProject(
            GlobalId=create_guid(),
            Name=project_name,
            OwnerHistory=self.owner_history,
            RepresentationContexts=[context],
            UnitsInContext=unit_assign,
        )

        # 空間構造
        self._create_spatial_hierarchy(project, create_guid)

    def _create_geometric_contexts(self):
        """幾何学表現コンテキストを作成"""
        context = self.file.createIfcGeometricRepresentationContext(
            ContextType="Model",
            CoordinateSpaceDimension=3,
            Precision=1e-5,
            WorldCoordinateSystem=self.file.createIfcAxis2Placement3D(
                Location=self.file.createIfcCartesianPoint([0.0, 0.0, 0.0])
            ),
        )

        self.model_context = self.file.createIfcGeometricRepresentationSubContext(
            ContextIdentifier="Body",
            ContextType="Model",
            ParentContext=context,
            TargetView="MODEL_VIEW",
        )

        self.plan_context = self.file.createIfcGeometricRepresentationSubContext(
            ContextIdentifier="Axis",
            ContextType="Plan",
            ParentContext=context,
            TargetView="PLAN_VIEW",
        )

    def _create_units(self) -> List:
        """単位系を作成"""
        return [
            self.file.createIfcSIUnit(
                UnitType="LENGTHUNIT", Name="METRE", Prefix="MILLI"
            ),
            self.file.createIfcSIUnit(UnitType="AREAUNIT", Name="SQUARE_METRE"),
            self.file.createIfcSIUnit(UnitType="VOLUMEUNIT", Name="CUBIC_METRE"),
            self.file.createIfcSIUnit(UnitType="PLANEANGLEUNIT", Name="RADIAN"),
        ]

    def _create_spatial_hierarchy(self, project, create_guid):
        """空間階層構造を作成"""
        # サイト
        site_placement = self.file.createIfcLocalPlacement(
            RelativePlacement=self.file.createIfcAxis2Placement3D(
                Location=self.file.createIfcCartesianPoint([0.0, 0.0, 0.0])
            )
        )
        site = self.file.createIfcSite(
            GlobalId=create_guid(),
            OwnerHistory=self.owner_history,
            Name="Site",
            CompositionType="ELEMENT",
            ObjectPlacement=site_placement,
        )
        self.file.createIfcRelAggregates(
            GlobalId=create_guid(),
            OwnerHistory=self.owner_history,
            RelatingObject=project,
            RelatedObjects=[site],
        )  # 建物
        self.building_placement = self.file.createIfcLocalPlacement(
            PlacementRelTo=site_placement,
            RelativePlacement=self.file.createIfcAxis2Placement3D(
                Location=self.file.createIfcCartesianPoint([0.0, 0.0, 0.0])
            ),
        )
        self.building = self.file.createIfcBuilding(
            GlobalId=create_guid(),
            OwnerHistory=self.owner_history,
            Name="Building",
            CompositionType="ELEMENT",
            ObjectPlacement=self.building_placement,
        )
        self.file.createIfcRelAggregates(
            GlobalId=create_guid(),
            OwnerHistory=self.owner_history,
            RelatingObject=site,
            RelatedObjects=[self.building],
        )

    def add_storey(
        self,
        name: str,
        elevation: float,
        create_guid_func=None,
    ):
        """BuildingStoreyを追加"""
        if create_guid_func is None:

            def create_guid_func():
                return create_ifc_guid()

        placement = self.file.createIfcLocalPlacement(
            PlacementRelTo=self.building_placement,
            RelativePlacement=self.file.createIfcAxis2Placement3D(
                Location=self.file.createIfcCartesianPoint([0.0, 0.0, float(elevation)])
            ),
        )
        storey = self.file.createIfcBuildingStorey(
            GlobalId=create_guid_func(),
            OwnerHistory=self.owner_history,
            Name=name,
            CompositionType="ELEMENT",
            ObjectPlacement=placement,
            Elevation=float(elevation),
        )
        self.file.createIfcRelAggregates(
            GlobalId=create_guid_func(),
            OwnerHistory=self.owner_history,
            RelatingObject=self.building,
            RelatedObjects=[storey],
        )
        return storey, placement

    def get_3d_context(self):
        """3D幾何学表現コンテキストを取得"""
        return self.model_context
