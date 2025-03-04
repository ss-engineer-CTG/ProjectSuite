import logging
from pathlib import Path
from typing import Optional
import sys

class LogManager:
    """ログ管理クラス"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初期化（シングルトンなので1回のみ実行）"""
        if self._initialized:
            return
        self._initialized = True
        
        # ログディレクトリの設定
        self.log_dir = Path('logs')
        self.log_file = self.log_dir / 'document_processor.log'
        
        # ログフォーマットの設定
        self.log_format = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        
        # 初期設定の実行
        self.setup_logging()
    
    def setup_logging(self, level: int = logging.INFO) -> None:
        """
        ログ設定のセットアップ
        
        Args:
            level: ログレベル（デフォルトはINFO）
        """
        try:
            # ログディレクトリの作成
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # ルートロガーの設定
            root_logger = logging.getLogger()
            root_logger.setLevel(level)
            
            # 既存のハンドラをクリア
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # ファイルハンドラの設定
            file_handler = logging.FileHandler(
                str(self.log_file),
                encoding='utf-8',
                mode='a'  # 追記モード
            )
            file_handler.setFormatter(logging.Formatter(self.log_format))
            root_logger.addHandler(file_handler)
            
            # コンソールハンドラの設定
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(self.log_format))
            root_logger.addHandler(console_handler)
            
            logging.info("Logging system initialized")
            
        except Exception as e:
            print(f"Error setting up logging: {str(e)}", file=sys.stderr)
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        ロガーを取得
        
        Args:
            name: ロガー名（省略時はルートロガー）
            
        Returns:
            logging.Logger: 設定済みのロガー
        """
        return logging.getLogger(name)