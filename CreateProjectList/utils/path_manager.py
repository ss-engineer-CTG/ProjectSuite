"""パス管理ユーティリティ"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from CreateProjectList.utils.log_manager import LogManager

class PathManager:
    """パス管理ユーティリティクラス"""
    
    logger = LogManager().get_logger(__name__)
    
    @staticmethod
    def normalize_path(path: Union[str, Path]) -> str:
        """
        パスを正規化する
        
        Args:
            path: 正規化するパス
            
        Returns:
            str: 正規化されたパス
        """
        try:
            if not path:
                return ""
                
            # Pathオブジェクトに変換して正規化
            normalized = str(Path(path).resolve())
            return normalized
            
        except Exception as e:
            PathManager.logger.error(f"パス正規化エラー: {e}")
            return str(path)
    
    @staticmethod
    def is_valid_path(path: Union[str, Path]) -> bool:
        """
        パスが有効かどうかチェック
        
        Args:
            path: チェックするパス
            
        Returns:
            bool: 有効な場合True
        """
        try:
            if not path:
                return False
                
            # 絶対パスに変換
            abs_path = Path(path).resolve()
            
            # 基本的な妥当性チェック
            # 1. パスの長さをチェック（Windowsの上限は260文字）
            if len(str(abs_path)) > 260:
                return False
                
            # 2. パスに無効な文字が含まれていないか
            # Windowsでの無効な文字: < > : " / \ | ? *
            if re.search(r'[<>:"/\\|?*]', str(abs_path.name)):
                return False
            
            # すべてのチェックを通過
            return True
            
        except Exception as e:
            PathManager.logger.error(f"パス検証エラー: {e}")
            return False
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> bool:
        """
        ディレクトリが存在することを確認し、必要なら作成
        
        Args:
            path: 確認/作成するディレクトリパス
            
        Returns:
            bool: 成功時True
        """
        try:
            if not path:
                return False
                
            directory = Path(path)
            directory.mkdir(parents=True, exist_ok=True)
            return True
            
        except Exception as e:
            PathManager.logger.error(f"ディレクトリ作成エラー: {e}")
            return False
    
    @staticmethod
    def get_user_directory() -> Path:
        """
        ユーザーディレクトリのパスを取得
        
        Returns:
            Path: ユーザードキュメントディレクトリのパス
        """
        try:
            # PathRegistryを使用して取得を試みる
            try:
                from PathRegistry import PathRegistry
                registry = PathRegistry.get_instance()
                user_data_dir = registry.get_path("USER_DATA_DIR")
                if user_data_dir:
                    return Path(user_data_dir)
            except (ImportError, Exception):
                pass
                
            # デフォルト値
            return Path.home() / "Documents" / "ProjectSuite"
            
        except Exception as e:
            PathManager.logger.error(f"ユーザーディレクトリ取得エラー: {e}")
            return Path.home() / "Documents" / "ProjectSuite"
    
    @staticmethod
    def get_relative_path(path: Union[str, Path], base: Union[str, Path]) -> Optional[Path]:
        """
        ベースパスからの相対パスを取得
        
        Args:
            path: 対象パス
            base: ベースパス
            
        Returns:
            Optional[Path]: 相対パス、取得できない場合はNone
        """
        try:
            path_obj = Path(path).resolve()
            base_obj = Path(base).resolve()
            
            # 相対パスを計算
            try:
                return path_obj.relative_to(base_obj)
            except ValueError:
                # 共通の親ディレクトリがない場合
                return None
                
        except Exception as e:
            PathManager.logger.error(f"相対パス計算エラー: {e}")
            return None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        ファイル名を安全な形式に変換
        
        Args:
            filename: 元のファイル名
            
        Returns:
            str: 安全なファイル名
        """
        try:
            # 無効な文字を置換
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # 長すぎる場合は切り詰め
            if len(safe_name) > 255:
                base, ext = os.path.splitext(safe_name)
                base = base[:255 - len(ext) - 1]
                safe_name = base + ext
                
            return safe_name
            
        except Exception as e:
            PathManager.logger.error(f"ファイル名サニタイズエラー: {e}")
            return filename

    @staticmethod
    def get_output_base_dir() -> Path:
        """
        出力ベースディレクトリを取得
        
        注: PathRegistryからOUTPUT_BASE_DIRを取得
        
        Returns:
            Path: 出力ベースディレクトリ
        """
        try:
            # PathRegistryからOUTPUT_BASE_DIRを取得
            try:
                from PathRegistry import PathRegistry
                registry = PathRegistry.get_instance()
                output_dir = registry.get_path("OUTPUT_BASE_DIR")
                if output_dir:
                    return Path(output_dir)
            except (ImportError, Exception) as e:
                PathManager.logger.warning(f"PathRegistry経由の出力パス取得エラー: {e}")
            
            # デフォルト値
            return Path.home() / "Desktop" / "projects"
        except Exception as e:
            PathManager.logger.error(f"出力ディレクトリ取得エラー: {e}")
            return Path.home() / "Desktop" / "projects"