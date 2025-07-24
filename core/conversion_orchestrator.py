"""Conversion Orchestrator

STB→IFC変換の統合オーケストレーター
依存性注入による疎結合アーキテクチャで全変換プロセスを統合管理
"""

from typing import Dict, Any, Optional, NamedTuple
import logging
from pathlib import Path

from core.service_container import ServiceContainer, get_global_container
from core.conversion_service import ConversionService
from exceptions.custom_errors import ConversionError

logger = logging.getLogger(__name__)


class ConversionResult(NamedTuple):
    """変換結果"""
    success: bool
    output_path: Optional[str] = None
    element_counts: Optional[Dict[str, int]] = None
    errors: Optional[list] = None
    warnings: Optional[list] = None


class ConversionOrchestrator:
    """STB→IFC変換の統合オーケストレーター
    
    Features:
    - 全変換プロセスの統合管理
    - 依存性注入による疎結合設計
    - エラーハンドリングとログ管理
    - 変換統計とメトリクス
    - テスト可能な設計
    """
    
    def __init__(self, service_container: Optional[ServiceContainer] = None):
        """ConversionOrchestratorの初期化
        
        Args:
            service_container: サービスコンテナ（テスト時のDI用）
        """
        self.container = service_container or get_global_container()
        
        # 実際の実装は既存のConversionServiceに委譲
        self.conversion_service = ConversionService()
        
        # 変換統計
        self._conversion_stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_elements_processed': 0
        }
        
        logger.info("ConversionOrchestrator initialized (delegating to ConversionService)")
    
    def convert(self, stb_path: str, output_path: str, **options) -> ConversionResult:
        """完全変換プロセス
        
        Args:
            stb_path: STBファイルパス
            output_path: 出力IFCファイルパス
            **options: 変換オプション
            
        Returns:
            ConversionResult: 変換結果
        """
        try:
            self._conversion_stats['total_conversions'] += 1
            logger.info(f"Starting conversion: {stb_path} -> {output_path}")
            
            # ConversionServiceの既存メソッドを順次呼び出し
            # 1. STBファイル読み込み
            stb_content = self.conversion_service.load_stb_file(stb_path)
            
            # 2. STB解析とIFC要素作成
            conversion_result = self.conversion_service.convert_stb_to_ifc(stb_content, stb_path)
            
            # 3. IFCファイル出力
            success = self.conversion_service.create_ifc_file(conversion_result, output_path)
            
            result_dict = {
                'success': success,
                'element_counts': conversion_result.get('element_counts', {}),
                'output_file': output_path
            }
            
            # 成功統計更新
            if result_dict.get('success', False):
                self._conversion_stats['successful_conversions'] += 1
                element_counts = result_dict.get('element_counts', {})
                if isinstance(element_counts, dict):
                    self._conversion_stats['total_elements_processed'] += sum(element_counts.values())
                
                logger.info(f"Conversion completed successfully: {output_path}")
                
                return ConversionResult(
                    success=True,
                    output_path=output_path,
                    element_counts=element_counts,
                    errors=[],
                    warnings=[]
                )
            else:
                error_msg = result_dict.get('error_message', 'Unknown conversion error')
                return ConversionResult(
                    success=False,
                    errors=[error_msg]
                )
            
        except ConversionError as e:
            self._conversion_stats['failed_conversions'] += 1
            logger.error(f"Conversion failed: {e}")
            return ConversionResult(
                success=False,
                errors=[str(e)]
            )
        except Exception as e:
            self._conversion_stats['failed_conversions'] += 1
            logger.error(f"Unexpected conversion error: {e}")
            return ConversionResult(
                success=False,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """変換統計情報を取得"""
        return self._conversion_stats.copy()
    
    def reset_stats(self):
        """統計情報をリセット"""
        self._conversion_stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_elements_processed': 0
        }
        logger.info("Conversion statistics reset")
    
    def validate_input(self, stb_path: str, output_path: str) -> tuple:
        """入力パラメータの検証
        
        Returns:
            (is_valid: bool, errors: list)
        """
        errors = []
        
        # STBファイルの存在確認
        if not Path(stb_path).exists():
            errors.append(f"STB file not found: {stb_path}")
        
        # 出力ディレクトリの確認
        output_dir = Path(output_path).parent
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create output directory: {e}")
        
        # ファイル拡張子の確認
        if not stb_path.lower().endswith('.stb'):
            errors.append(f"Invalid STB file extension: {stb_path}")
        
        if not output_path.lower().endswith('.ifc'):
            errors.append(f"Invalid IFC file extension: {output_path}")
        
        return len(errors) == 0, errors
    
    def get_supported_element_types(self) -> list:
        """サポートされている要素タイプのリスト"""
        return ['beam', 'column', 'slab', 'wall', 'brace', 'pile', 'footing', 'foundation_column']