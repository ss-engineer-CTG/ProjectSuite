"""
CreateProjectList Package
ドキュメント処理アプリケーション
"""
from pathlib import Path
import sys

# パッケージのルートディレクトリを取得
package_root = Path(__file__).parent.absolute()

# パッケージのルートをsys.pathに追加（存在しない場合のみ）
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

# バージョン情報
__version__ = '1.1.0'

# メインコンポーネントをインポート
from .main import DocumentProcessor
from .main import main
from .gui import DocumentProcessorGUI

# プロセッサーをインポート
from .processors import (
    DocumentProcessorBase,
    DocumentProcessorFactory,
    XLSXProcessor,
    XLSProcessor,
    DOCProcessor,
    DOCXProcessor,
    FolderProcessor
)

# ユーティリティをインポート
from .utils import (
    ConfigManager,
    DatabaseContext,
    FileLock,
    PathManager,
    TransactionContext,
    LogManager
)

__all__ = [
    # メインコンポーネント
    'DocumentProcessor',
    'DocumentProcessorGUI',
    'main',

    # プロセッサー
    'DocumentProcessorBase',
    'DocumentProcessorFactory',
    'XLSXProcessor',
    'XLSProcessor',
    'DOCProcessor',
    'DOCXProcessor',
    'FolderProcessor',

    # ユーティリティ
    'ConfigManager',
    'DatabaseContext',
    'FileLock',
    'PathManager',
    'TransactionContext',
    'LogManager'
]