# path_manager.py

from pathlib import Path
import os
from typing import Optional

class PathManager:
    """パス管理クラス"""
    
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
        except ImportError:
            pass  # PathRegistryが使えない場合は通常の正規化に進む
            
        normalized = str(Path(path).resolve())
        return normalized
    
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
        except Exception:
            return False
    
    @staticmethod
    def ensure_directory(path: str) -> None:
        """
        ディレクトリの存在確認と作成
        
        Args:
            path: 確認/作成するディレクトリパス
        """
        if not path:
            return
            
        dir_path = Path(path)
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
        elif not dir_path.is_dir():
            raise ValueError(f"{path} is not a directory")
    
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