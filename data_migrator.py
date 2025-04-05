"""
データ移行ユーティリティ
ユーザードキュメントフォルダへのデータコピー処理を担当
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

# ロガーの設定
logger = logging.getLogger(__name__)

class DataMigrator:
    """データ移行処理を提供するユーティリティクラス"""
    
    # コピー対象サブディレクトリ
    TARGET_SUBDIRS = [
        "exports",
        "master",
        "projects",
        "templates",
        "temp",
        "backup"
    ]
    
    # 必須のデータファイル
    CRITICAL_FILES = [
        "projects.db",
        "master/factory_info.csv",
        "exports/dashboard.csv",
        "exports/projects.csv"
    ]
    
    def __init__(self, registry):
        """
        初期化
        
        Args:
            registry: PathRegistryのインスタンス
        """
        self.registry = registry
        self.root_dir = Path(registry.get_path("ROOT"))
        self.data_dir = Path(registry.get_path("DATA_DIR"))
        self.copied_files = []
        self.failed_files = []
    
    def migrate_data(self) -> Dict[str, Any]:
        """
        データ移行を実行
        
        Returns:
            Dict[str, Any]: 移行結果情報
        """
        try:
            # データソースを検索
            source = self._find_data_source()
            if not source:
                logger.warning("データソースが見つかりません。空のデータディレクトリ構造を作成します。")
                self._create_empty_structure()
                return {
                    'success': True,
                    'source': None,
                    'destination': str(self.data_dir),
                    'copied_files': 0,
                    'failed_files': 0,
                    'message': "空のディレクトリ構造を作成しました"
                }
            
            logger.info(f"データ移行を開始: {source} -> {self.data_dir}")
            
            # サブディレクトリのコピー
            for subdir in self.TARGET_SUBDIRS:
                src_dir = source / subdir
                dst_dir = self.data_dir / subdir
                
                if src_dir.exists():
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    self._copy_directory_contents(src_dir, dst_dir)
            
            # データベースファイルのコピー
            db_file = source / "projects.db"
            if db_file.exists():
                try:
                    shutil.copy2(db_file, self.data_dir / "projects.db")
                    self.copied_files.append(str(db_file))
                    logger.info(f"データベースファイルをコピー: {db_file} -> {self.data_dir / 'projects.db'}")
                except Exception as e:
                    self.failed_files.append(str(db_file))
                    logger.error(f"データベースファイルのコピーに失敗: {e}")
            
            # 結果の返却
            return {
                'success': True,
                'source': str(source),
                'destination': str(self.data_dir),
                'copied_files': len(self.copied_files),
                'failed_files': len(self.failed_files),
                'message': "データ移行が完了しました"
            }
        except Exception as e:
            logger.error(f"データ移行エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'copied_files': len(self.copied_files),
                'failed_files': len(self.failed_files),
                'message': f"データ移行に失敗しました: {e}"
            }
    
    def _find_data_source(self) -> Optional[Path]:
        """
        データソースディレクトリを検索
        
        Returns:
            Optional[Path]: 検出されたデータソースパス
        """
        # レジストリから検索機能を使用
        if hasattr(self.registry, 'find_data_source'):
            source = self.registry.find_data_source()
            if source:
                return source
        
        # 検索場所のリスト（優先順位順）
        potential_paths = [
            # アプリケーションのデータディレクトリ
            self.root_dir / "data",
            
            # ProjectManagerのデータディレクトリ（複数の可能性）
            self.root_dir / "ProjectManager" / "data",
            Path(os.getcwd()) / "ProjectManager" / "data",
            
            # 開発環境でよく使われるパス
            Path.home() / "Documents" / "Projects" / "ProjectSuite" / "ProjectManager" / "data",
            Path.home() / "Projects" / "ProjectSuite" / "ProjectManager" / "data"
        ]
        
        # パスが存在するか確認
        for path in potential_paths:
            if path.exists() and path.is_dir():
                # 実際にデータらしきものが存在するか確認
                has_content = any([
                    (path / "projects").exists(),
                    (path / "templates").exists(),
                    (path / "master").exists(),
                    (path / "projects.db").exists()
                ])
                
                if has_content:
                    logger.info(f"データソースディレクトリを発見: {path}")
                    return path
        
        # 見つからない場合
        logger.warning("データソースディレクトリが見つかりませんでした")
        return None
    
    def _copy_directory_contents(self, src_dir: Path, dst_dir: Path) -> None:
        """
        ディレクトリ内容をコピー
        
        Args:
            src_dir: ソースディレクトリ
            dst_dir: コピー先ディレクトリ
        """
        try:
            # ディレクトリが存在することを確認
            if not src_dir.exists() or not src_dir.is_dir():
                logger.warning(f"ソースディレクトリが存在しません: {src_dir}")
                return
                
            # ディレクトリ内のファイルを列挙
            for item in src_dir.rglob("*"):
                if item.is_file():
                    # 相対パスを計算
                    rel_path = item.relative_to(src_dir)
                    dst_path = dst_dir / rel_path
                    
                    # ディレクトリ構造を作成
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        # ファイルのコピー
                        shutil.copy2(item, dst_path)
                        self.copied_files.append(str(item))
                        logger.debug(f"ファイルをコピー: {item} -> {dst_path}")
                    except Exception as e:
                        self.failed_files.append(str(item))
                        logger.error(f"ファイルコピーエラー {item}: {e}")
        except Exception as e:
            logger.error(f"ディレクトリコピーエラー {src_dir}: {e}")
    
    def _create_empty_structure(self) -> None:
        """
        空のデータディレクトリ構造を作成
        """
        try:
            # 基本ディレクトリ構造の作成
            for subdir in self.TARGET_SUBDIRS:
                (self.data_dir / subdir).mkdir(parents=True, exist_ok=True)
                logger.debug(f"ディレクトリを作成: {self.data_dir / subdir}")
        except Exception as e:
            logger.error(f"空のディレクトリ構造作成エラー: {e}")