"""パス管理ユーティリティ"""

from pathlib import Path
import os
from typing import Optional
import logging
from CreateProjectList.utils.log_manager import LogManager

class PathManager:
    """パス管理クラス"""
    
    logger = LogManager().get_logger(__name__)
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """
        パスを正規化
        - 相対パスを絶対パスに変換
        - パスセパレータを統一
        - 余分なセパレータを除去
        
        Args:
            path: 正規化するパス
            
        Returns:
            str: 正規化されたパス
        """
        if not path:
            return ""
        
        # PathRegistryを使用してパスを正規化
        try:
            from PathRegistry import PathRegistry
            registry = PathRegistry.get_instance()
            
            # レジストリからのパス解決を試みる
            for key, registered_path in registry.get_all_paths().items():
                if str(registered_path) == str(path):
                    resolved_path = registry.get_path(key)
                    if resolved_path:
                        return str(resolved_path)
                        
            # キーではなくパス文字列が直接一致する場合
            registry_paths = registry.get_all_paths()
            if path in registry_paths:
                return registry_paths[path]
                
        except ImportError:
            PathManager.logger.debug("PathRegistryが使用できません。基本的なパス正規化を使用します。")
        except Exception as e:
            PathManager.logger.warning(f"レジストリによるパス解決エラー: {e}")
            
        try:
            normalized = str(Path(path).resolve())
            return normalized
        except Exception as e:
            PathManager.logger.warning(f"パス正規化エラー: {e}")
            return path
    
    @staticmethod
    def is_valid_path(path: str) -> bool:
        """
        パスの妥当性チェック
        
        Args:
            path: チェックするパス
            
        Returns:
            bool: パスが有効な場合True
        """
        if not path:
            return False
            
        try:
            path_obj = Path(path)
            # 絶対パスであることを確認
            return path_obj.is_absolute()
        except Exception as e:
            PathManager.logger.warning(f"パス検証エラー: {e}")
            return False
    
    @staticmethod
    def ensure_directory(path: str) -> bool:
        """
        ディレクトリの存在確認と作成
        
        Args:
            path: 確認/作成するディレクトリパス
            
        Returns:
            bool: 成功時True
        """
        if not path:
            return False
            
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                PathManager.logger.info(f"ディレクトリを作成: {dir_path}")
            elif not dir_path.is_dir():
                PathManager.logger.warning(f"{path} はディレクトリではありません")
                return False
            return True
        except Exception as e:
            PathManager.logger.error(f"ディレクトリ作成エラー: {e}")
            return False
    
    @staticmethod
    def get_relative_path(path: str, base_path: str) -> str:
        """
        ベースパスからの相対パスを取得
        
        Args:
            path: 対象パス
            base_path: ベースパス
            
        Returns:
            str: 相対パス
        """
        if not path or not base_path:
            return path
            
        try:
            return str(Path(path).relative_to(base_path))
        except ValueError:
            return path
    
    @staticmethod
    def join_paths(*paths: str) -> str:
        """
        パスの結合
        
        Args:
            *paths: 結合するパスの可変長引数
            
        Returns:
            str: 結合されたパス
        """
        if not paths:
            return ""
            
        return str(Path(*paths))
    
    @staticmethod
    def get_file_extension(path: str) -> str:
        """
        ファイル拡張子を取得
        
        Args:
            path: ファイルパス
            
        Returns:
            str: 拡張子（ドット付き、小文字）
        """
        if not path:
            return ""
            
        return Path(path).suffix.lower()
    
    @staticmethod
    def change_extension(path: str, new_ext: str) -> str:
        """
        ファイル拡張子を変更
        
        Args:
            path: ファイルパス
            new_ext: 新しい拡張子（ドットの有無は任意）
            
        Returns:
            str: 拡張子が変更されたパス
        """
        if not path:
            return ""
            
        if not new_ext.startswith('.'):
            new_ext = '.' + new_ext
        return str(Path(path).with_suffix(new_ext))
    
    @staticmethod
    def sanitize_path(path_component: str) -> str:
        """
        パスコンポーネントから不正な文字を除去
        
        Args:
            path_component: パスの構成要素（フォルダ名やファイル名）
            
        Returns:
            str: サニタイズされたパスコンポーネント
        """
        # Windowsで使用できない文字を置換
        invalid_chars = '<>:"/\\|?*'
        result = path_component
        for char in invalid_chars:
            result = result.replace(char, '_')
        
        # 先頭や末尾のスペースやピリオドを除去
        result = result.strip(' .')
        
        # 空の場合はデフォルト名を使用
        if not result:
            result = "unnamed"
            
        return result
        
    @staticmethod
    def get_user_directory() -> Path:
        """
        アプリケーション用のユーザードキュメントディレクトリを取得
        
        Returns:
            Path: ユーザードキュメントディレクトリ
        """
        try:
            from PathRegistry import PathRegistry
            registry = PathRegistry.get_instance()
            user_dir = registry.get_path("USER_DATA_DIR")
            if user_dir:
                return Path(user_dir)
        except Exception:
            pass
            
        # デフォルトのユーザードキュメントディレクトリ
        return Path.home() / "Documents" / "ProjectSuite"