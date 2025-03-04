"""統合機能パッケージ

このパッケージは、ProjectManagerとCreateProjectListの統合機能を提供します。
主な機能：
- ドキュメント処理機能の統合管理
- 設定の解決と検証
- エラーハンドリング
"""

from .document_processor_manager import DocumentProcessorManager
from .config_resolver import ConfigResolver
from .error_handler import (
    IntegrationError,
    ConfigurationError,
    WindowError,
    ResourceError,
    IntegrationErrorHandler
)

__all__ = [
    'DocumentProcessorManager',
    'ConfigResolver',
    'IntegrationError',
    'ConfigurationError',
    'WindowError',
    'ResourceError',
    'IntegrationErrorHandler'
]

# バージョン情報
__version__ = '1.0.0'