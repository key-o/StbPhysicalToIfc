"""
ElementCentricConfig - 要素中心アプローチの設定管理
環境変数、設定ファイル、実行時設定による動作制御
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
from utils.logger import get_logger

from core.element_centric_integration_service import ConversionMode, IntegrationConfig


@dataclass
class ElementCentricSettings:
    """要素中心アプローチの全体設定"""
    # 基本設定
    enabled: bool = True
    default_mode: str = "hybrid"
    
    # パフォーマンス設定
    enable_performance_monitoring: bool = True
    performance_comparison_enabled: bool = False
    processing_timeout_ms: float = 30000.0
    
    # 品質設定
    duplicate_tolerance: int = 0
    confidence_threshold: float = 0.7
    validation_enabled: bool = True
    
    # フォールバック設定
    enable_fallback: bool = True
    fallback_threshold_ms: float = 5000.0
    max_fallback_attempts: int = 1
    
    # ログ設定
    enable_detailed_logging: bool = False
    log_performance_metrics: bool = True
    log_conversion_statistics: bool = True
    
    # 実験的機能
    enable_experimental_features: bool = False
    parallel_processing_enabled: bool = False
    memory_optimization_enabled: bool = True


class ElementCentricConfigManager:
    """要素中心アプローチの設定管理クラス"""
    
    def __init__(self, config_file_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.config_file_path = config_file_path or self._get_default_config_path()
        self.settings = ElementCentricSettings()
        
        # 設定の読み込み順序
        self._load_default_settings()
        self._load_config_file()
        self._load_environment_variables()
        
        self.logger.info("ElementCentricConfigManager初期化完了")
    
    def _get_default_config_path(self) -> str:
        """デフォルト設定ファイルパスの取得"""
        return os.path.join(
            os.path.dirname(__file__), 
            "element_centric_settings.json"
        )
    
    def _load_default_settings(self):
        """デフォルト設定の読み込み"""
        # データクラスのデフォルト値が既に設定済み
        self.logger.debug("デフォルト設定読み込み完了")
    
    def _load_config_file(self):
        """設定ファイルからの設定読み込み"""
        config_path = Path(self.config_file_path)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 設定を更新
                for key, value in config_data.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
                        self.logger.debug("設定更新: %s = %s", key, value)
                
                self.logger.info("設定ファイル読み込み完了: %s", config_path)
                
            except Exception as e:
                self.logger.warning("設定ファイル読み込み失敗: %s - デフォルト設定を使用", str(e))
        else:
            self.logger.info("設定ファイルが存在しません - デフォルト設定を使用: %s", config_path)
    
    def _load_environment_variables(self):
        """
        環境変数からの設定読み込み
        
        Debug Notes:
            - STB2IFC_*プレフィックスの環境変数を検索
            - 型変換エラーは警告ログを出力してスキップ
            - 設定の優先順位: 環境変数 > 設定ファイル > デフォルト値
        """
        env_mappings = {
            'STB2IFC_ELEMENT_CENTRIC_ENABLED': ('enabled', bool),
            'STB2IFC_DEFAULT_MODE': ('default_mode', str),
            'STB2IFC_ENABLE_FALLBACK': ('enable_fallback', bool),
            'STB2IFC_CONFIDENCE_THRESHOLD': ('confidence_threshold', float),
            'STB2IFC_DUPLICATE_TOLERANCE': ('duplicate_tolerance', int),
            'STB2IFC_DETAILED_LOGGING': ('enable_detailed_logging', bool),
            'STB2IFC_PERFORMANCE_MONITORING': ('enable_performance_monitoring', bool),
            'STB2IFC_PROCESSING_TIMEOUT': ('processing_timeout_ms', float),
        }
        
        updated_count = 0
        skipped_vars = []
        
        # DEBUG: 環境変数読み込み開始
        self.logger.debug("DEBUG: 環境変数読み込み開始 - 対象変数数: %d", len(env_mappings))
        
        for env_var, (attr_name, attr_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            
            if env_value is not None:
                try:
                    # 型変換
                    if attr_type == bool:
                        # boolの場合の変換詳細ログ
                        value = env_value.lower() in ('true', '1', 'yes', 'on')
                        self.logger.debug("DEBUG: bool変換 - %s: '%s' -> %s", env_var, env_value, value)
                    elif attr_type == int:
                        value = int(env_value)
                        self.logger.debug("DEBUG: int変換 - %s: '%s' -> %d", env_var, env_value, value)
                    elif attr_type == float:
                        value = float(env_value)
                        self.logger.debug("DEBUG: float変換 - %s: '%s' -> %.2f", env_var, env_value, value)
                    else:
                        value = env_value
                        self.logger.debug("DEBUG: str設定 - %s: '%s'", env_var, env_value)
                    
                    # 設定更新前の値を記録（デバッグ用）
                    old_value = getattr(self.settings, attr_name)
                    setattr(self.settings, attr_name, value)
                    
                    if old_value != value:
                        self.logger.debug("環境変数設定更新: %s = %s (旧値: %s)", attr_name, value, old_value)
                    else:
                        self.logger.debug("環境変数設定（値変更なし): %s = %s", attr_name, value)
                    
                    updated_count += 1
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning("WARNING: 環境変数変換エラー %s='%s': %s", env_var, env_value, str(e))
                    skipped_vars.append(env_var)
            else:
                # 環境変数が設定されていない場合もデバッグログに記録
                self.logger.debug("DEBUG: 環境変数未設定 - %s", env_var)
        
        # DEBUG: 環境変数読み込み結果サマリー
        if updated_count > 0:
            self.logger.info("環境変数から%d個の設定を更新", updated_count)
        if skipped_vars:
            self.logger.warning("WARNING: %d個の環境変数をスキップ: %s", len(skipped_vars), ', '.join(skipped_vars))
    
    def get_integration_config(self) -> IntegrationConfig:
        """統合サービス用の設定を生成"""
        try:
            conversion_mode = ConversionMode(self.settings.default_mode)
        except ValueError:
            self.logger.warning("無効な変換モード: %s - hybridを使用", self.settings.default_mode)
            conversion_mode = ConversionMode.HYBRID
        
        return IntegrationConfig(
            conversion_mode=conversion_mode,
            enable_fallback=self.settings.enable_fallback,
            enable_performance_comparison=self.settings.performance_comparison_enabled,
            fallback_threshold_ms=self.settings.fallback_threshold_ms,
            duplicate_tolerance=self.settings.duplicate_tolerance,
            confidence_threshold=self.settings.confidence_threshold,
            enable_detailed_logging=self.settings.enable_detailed_logging
        )
    
    def save_config_file(self, file_path: Optional[str] = None):
        """設定をファイルに保存"""
        save_path = file_path or self.config_file_path
        
        try:
            config_data = asdict(self.settings)
            
            # ディレクトリが存在しない場合は作成
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("設定ファイル保存完了: %s", save_path)
            
        except Exception as e:
            self.logger.error("設定ファイル保存失敗: %s", str(e))
            raise
    
    def update_setting(self, key: str, value: Any):
        """実行時設定更新"""
        if hasattr(self.settings, key):
            old_value = getattr(self.settings, key)
            setattr(self.settings, key, value)
            self.logger.info("設定更新: %s: %s -> %s", key, old_value, value)
        else:
            raise ValueError(f"未知の設定キー: {key}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """設定値の取得"""
        return getattr(self.settings, key, default)
    
    def is_enabled(self) -> bool:
        """要素中心アプローチが有効かどうか"""
        return self.settings.enabled
    
    def should_use_fallback(self, processing_time_ms: float) -> bool:
        """フォールバックを使用すべきかどうか"""
        return (
            self.settings.enable_fallback and 
            processing_time_ms > self.settings.fallback_threshold_ms
        )
    
    def get_performance_config(self) -> Dict[str, Any]:
        """パフォーマンス関連設定の取得"""
        return {
            'monitoring_enabled': self.settings.enable_performance_monitoring,
            'comparison_enabled': self.settings.performance_comparison_enabled,
            'timeout_ms': self.settings.processing_timeout_ms,
            'log_metrics': self.settings.log_performance_metrics
        }
    
    def get_quality_config(self) -> Dict[str, Any]:
        """品質関連設定の取得"""
        return {
            'duplicate_tolerance': self.settings.duplicate_tolerance,
            'confidence_threshold': self.settings.confidence_threshold,
            'validation_enabled': self.settings.validation_enabled
        }
    
    def create_sample_config(self, output_path: str):
        """サンプル設定ファイルの作成"""
        sample_settings = ElementCentricSettings()
        sample_data = asdict(sample_settings)
        
        # コメント付きサンプル設定
        sample_with_comments = {
            "_comment": "STB2IFC 要素中心アプローチ設定ファイル",
            "_version": "1.0",
            "enabled": {
                "_comment": "要素中心アプローチを有効にするかどうか",
                "value": sample_data["enabled"]
            },
            "default_mode": {
                "_comment": "デフォルト変換モード: legacy, element_centric, hybrid, auto",
                "value": sample_data["default_mode"]
            },
            "enable_fallback": {
                "_comment": "エラー時のフォールバック機能を有効にするかどうか",
                "value": sample_data["enable_fallback"]
            },
            "confidence_threshold": {
                "_comment": "階層判定の信頼度閾値 (0.0-1.0)",
                "value": sample_data["confidence_threshold"]
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample_with_comments, f, indent=2, ensure_ascii=False)
        
        self.logger.info("サンプル設定ファイル作成: %s", output_path)
    
    def validate_config(self) -> List[str]:
        """設定の妥当性検証"""
        warnings = []
        
        # 閾値の範囲チェック
        if not (0.0 <= self.settings.confidence_threshold <= 1.0):
            warnings.append(f"confidence_threshold が範囲外: {self.settings.confidence_threshold}")
        
        # タイムアウトの妥当性チェック
        if self.settings.processing_timeout_ms < 1000:
            warnings.append(f"processing_timeout_ms が短すぎます: {self.settings.processing_timeout_ms}")
        
        # モードの妥当性チェック
        valid_modes = [mode.value for mode in ConversionMode]
        if self.settings.default_mode not in valid_modes:
            warnings.append(f"無効なdefault_mode: {self.settings.default_mode}")
        
        # 重複許容数の妥当性チェック
        if self.settings.duplicate_tolerance < 0:
            warnings.append(f"duplicate_tolerance が負の値: {self.settings.duplicate_tolerance}")
        
        return warnings
    
    def print_current_config(self):
        """現在の設定を表示"""
        print("=" * 50)
        print("要素中心アプローチ 現在の設定")
        print("=" * 50)
        
        config_dict = asdict(self.settings)
        for key, value in config_dict.items():
            print(f"{key:30}: {value}")
        
        # 設定妥当性の確認
        warnings = self.validate_config()
        if warnings:
            print("\n⚠️ 設定警告:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\n✅ 設定は正常です")


# グローバル設定管理インスタンス
_config_manager: Optional[ElementCentricConfigManager] = None


def get_config_manager() -> ElementCentricConfigManager:
    """グローバル設定管理インスタンスの取得"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ElementCentricConfigManager()
    return _config_manager


def reload_config():
    """設定の再読み込み"""
    global _config_manager
    _config_manager = None
    return get_config_manager()