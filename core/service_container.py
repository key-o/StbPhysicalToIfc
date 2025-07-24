"""Service Container

サービス依存関係管理コンテナ
依存性注入（Dependency Injection）による疎結合アーキテクチャの実現
"""

from typing import Dict, Type, TypeVar, Optional, Any, Callable
import logging
from abc import ABC, abstractmethod

from ifcCreator.services.profile_service import ProfileService
from ifcCreator.services.property_service import PropertyService
from ifcCreator.services.geometry_service import GeometryService
from ifcCreator.creators.material_creator import MaterialCreator

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceInterface(ABC):
    """サービスインターフェースの基底クラス"""

    pass


class ServiceContainer:
    """サービス依存関係管理コンテナ

    Features:
    - サービスの登録と取得
    - シングルトンパターン対応
    - ファクトリ関数対応
    - 循環依存の検出
    - デフォルトサービスの自動設定
    """

    def __init__(self):
        """ServiceContainerの初期化"""
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._resolving: set = set()  # 循環依存検出用

        # IFCファイルとモデルコンテキストの保持
        self._ifc_file = None
        self._model_context = None

        self._configure_default_services()

    def _configure_default_services(self):
        """デフォルトサービスの設定"""
        # デフォルトのサービス登録
        self.register_factory(ProfileService, self._create_profile_service)
        self.register_factory(PropertyService, self._create_property_service)
        self.register_factory(GeometryService, self._create_geometry_service)
        self.register_factory(MaterialCreator, self._create_material_creator)

        logger.info("Default services configured")

    def register_service(
        self, interface_type: Type[T], implementation: T, singleton: bool = True
    ):
        """サービスの登録

        Args:
            interface_type: サービスインターフェースタイプ
            implementation: 実装インスタンス
            singleton: シングルトンとして管理するか
        """
        if singleton:
            self._singletons[interface_type] = implementation
        else:
            self._services[interface_type] = implementation

        logger.debug(
            f"Service registered: {interface_type.__name__} -> {type(implementation).__name__}"
        )

    def register_factory(self, interface_type: Type[T], factory: Callable[[], T]):
        """ファクトリ関数の登録

        Args:
            interface_type: サービスインターフェースタイプ
            factory: ファクトリ関数
        """
        self._factories[interface_type] = factory
        logger.debug(f"Factory registered: {interface_type.__name__}")

    def get_service(self, interface_type: Type[T]) -> Optional[T]:
        """サービスの取得

        Args:
            interface_type: サービスインターフェースタイプ

        Returns:
            サービスインスタンス

        Raises:
            RuntimeError: 循環依存が検出された場合
        """
        # 循環依存チェック
        if interface_type in self._resolving:
            raise RuntimeError(
                f"Circular dependency detected for {interface_type.__name__}"
            )

        # シングルトンキャッシュから取得
        if interface_type in self._singletons:
            return self._singletons[interface_type]

        # 直接登録されたサービスから取得
        if interface_type in self._services:
            return self._services[interface_type]

        # ファクトリから作成
        if interface_type in self._factories:
            self._resolving.add(interface_type)
            try:
                service = self._factories[interface_type]()
                self._singletons[interface_type] = (
                    service  # シングルトンとしてキャッシュ
                )
                logger.debug(f"Service created via factory: {interface_type.__name__}")
                return service
            finally:
                self._resolving.remove(interface_type)

        logger.warning(f"Service not found: {interface_type.__name__}")
        return None

    def create_creator(self, element_type: str):
        """Creator生成（DI対応）

        Args:
            element_type: 要素タイプ (beam, column, slab, wall, etc.)

        Returns:
            DIされたCreatorインスタンス
        """
        try:
            creator_class = self._get_creator_class(element_type)
            if not creator_class:
                logger.error(f"Unknown element type for creator: {element_type}")
                return None

            # サービス依存関係を注入
            services = {
                "profile_service": self.get_service(ProfileService),
                "property_service": self.get_service(PropertyService),
                "geometry_service": self.get_service(GeometryService),
            }

            # Creatorインスタンスを作成（サービス注入）
            return creator_class(**services)

        except Exception as e:
            logger.error(f"Failed to create creator for {element_type}: {e}")
            return None

    def _get_creator_class(self, element_type: str) -> Optional[Type]:
        """要素タイプに対応するCreatorクラスを取得"""
        creator_mapping = {
            "beam": "IFCBeamCreatorRefactored",
            "column": "IFCColumnCreatorRefactored",
            "slab": "IFCSlabCreatorRefactored",
            "wall": "IFCWallCreatorRefactored",
            "brace": "IFCBraceCreatorRefactored",
        }

        creator_name = creator_mapping.get(element_type)
        if not creator_name:
            return None

        try:
            # 動的インポート
            if element_type == "beam":
                from ifcCreator.beam_creator_refactored import IFCBeamCreatorRefactored

                return IFCBeamCreatorRefactored
            elif element_type == "column":
                from ifcCreator.column_creator_refactored import (
                    IFCColumnCreatorRefactored,
                )

                return IFCColumnCreatorRefactored
            elif element_type == "slab":
                from ifcCreator.slab_creator_refactored import IFCSlabCreatorRefactored

                return IFCSlabCreatorRefactored
            elif element_type == "wall":
                from ifcCreator.wall_creator_refactored import IFCWallCreatorRefactored

                return IFCWallCreatorRefactored
            elif element_type == "brace":
                from ifcCreator.brace_creator_refactored import (
                    IFCBraceCreatorRefactored,
                )

                return IFCBraceCreatorRefactored

        except ImportError as e:
            logger.error(f"Failed to import creator for {element_type}: {e}")
            return None

    def _create_profile_service(self) -> ProfileService:
        """ProfileServiceファクトリ"""
        # v2.2.0: 実際のIFCファイルとコンテキストが必要な場合は、configure_servicesで設定
        return ProfileService(ifc_file=self._ifc_file)

    def _create_property_service(self) -> PropertyService:
        """PropertyServiceファクトリ"""
        return PropertyService(ifc_file=self._ifc_file)

    def _create_geometry_service(self) -> GeometryService:
        """GeometryServiceファクトリ"""
        return GeometryService(
            ifc_file=self._ifc_file, model_context=self._model_context
        )

    def _create_material_creator(self) -> MaterialCreator:
        """MaterialCreatorファクトリ"""
        # MaterialCreatorは既存のowner_historyが必要なため、プロジェクトビルダーから取得
        return MaterialCreator(
            ifc_file=self._ifc_file, owner_history=None  # 後で設定
        )

    def configure_services(self, ifc_file, model_context, profile_factory=None, owner_history=None):
        """実際のIFCファイルとコンテキストでサービスを再設定

        Args:
            ifc_file: IFCファイルオブジェクト
            model_context: モデルコンテキスト
            profile_factory: プロファイルファクトリ
            owner_history: オーナー履歴（MaterialCreator用）
        """
        # 内部状態を更新
        self._ifc_file = ifc_file
        self._model_context = model_context

        # 既存のシングルトンをクリア
        self._singletons.clear()

        # 実際のコンテキストでサービスを再作成
        profile_service = ProfileService(ifc_file)
        property_service = PropertyService(ifc_file)
        geometry_service = GeometryService(ifc_file, model_context)
        material_creator = MaterialCreator(ifc_file, owner_history)

        # シングルトンとして登録
        self.register_service(ProfileService, profile_service, singleton=True)
        self.register_service(PropertyService, property_service, singleton=True)
        self.register_service(GeometryService, geometry_service, singleton=True)
        self.register_service(MaterialCreator, material_creator, singleton=True)

        logger.info("Services configured with actual IFC context")

    def clear_services(self):
        """全サービスをクリア"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._resolving.clear()
        logger.info("All services cleared")

    def get_service_stats(self) -> Dict[str, Any]:
        """サービス統計情報を取得"""
        return {
            "registered_services": len(self._services),
            "singletons": len(self._singletons),
            "factories": len(self._factories),
            "service_types": [service.__name__ for service in self._services.keys()],
            "singleton_types": [
                service.__name__ for service in self._singletons.keys()
            ],
            "factory_types": [service.__name__ for service in self._factories.keys()],
        }


# グローバルサービスコンテナインスタンス
_global_container: Optional[ServiceContainer] = None


def get_global_container() -> ServiceContainer:
    """グローバルサービスコンテナを取得"""
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer()
    return _global_container


def configure_global_services(ifc_file, model_context, profile_factory=None):
    """グローバルサービスを設定"""
    container = get_global_container()
    container.configure_services(ifc_file, model_context, profile_factory)
