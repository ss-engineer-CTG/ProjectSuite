"""フォルダ名処理とディレクトリ構造管理クラス"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import os
import shutil
import logging
from datetime import datetime
from CreateProjectList.utils.path_manager import PathManager
from CreateProjectList.utils.log_manager import LogManager

class FolderProcessorError(Exception):
    """フォルダ処理に関連するエラー"""
    pass

class FolderProcessor:
    """フォルダ名処理とディレクトリ構造管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = LogManager().get_logger(self.__class__.__name__)
        self._processed_paths: List[Path] = []

    def validate_output_location(self, input_path: Path, output_path: Path) -> Tuple[bool, List[str]]:
        """
        出力先の妥当性を検証

        Args:
            input_path: 入力フォルダのパス
            output_path: 出力フォルダのパス

        Returns:
            Tuple[bool, List[str]]: 
                - 検証結果（True: 問題なし、False: 既存項目あり）
                - 既存項目のパスリスト
        """
        existing_items = []

        try:
            # 入力パスの検証
            if not input_path.exists():
                raise FolderProcessorError("入力フォルダが存在しません")
            if not input_path.is_dir():
                raise FolderProcessorError("入力パスがフォルダではありません")

            # 入力フォルダ内の全項目を取得（.gitなどの隠しファイルは除外）
            input_items = [
                item for item in input_path.rglob('*')
                if not any(part.startswith('.') for part in item.parts)
            ]
            
            if not input_items:
                raise FolderProcessorError("入力フォルダが空です")

            # 出力パスの検証
            if not output_path.parent.exists():
                try:
                    output_path.parent.mkdir(parents=True)
                except Exception as e:
                    raise FolderProcessorError(f"出力先親フォルダの作成に失敗しました: {e}")

            # 書き込み権限の確認
            try:
                test_file = output_path / '.write_test'
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                raise FolderProcessorError(f"出力先への書き込み権限がありません: {e}")

            # 既存項目のチェック
            for item in input_items:
                # 入力パスからの相対パスを取得
                relative_path = item.relative_to(input_path)
                # 出力先での対応するパスを構築
                target_path = output_path / relative_path

                # パスが既に存在するかチェック
                if target_path.exists():
                    existing_items.append(str(target_path))

            return len(existing_items) == 0, existing_items

        except FolderProcessorError:
            raise
        except Exception as e:
            self.logger.error(f"出力先の検証エラー: {e}")
            raise FolderProcessorError(f"出力先の検証中にエラーが発生しました: {e}")

    def process_path(self, path: Path, replacements: Dict[str, str]) -> Path:
        """
        パス全体を処理し、必要なフォルダを作成
        
        Args:
            path: 処理対象パス
            replacements: 置換ルール辞書
            
        Returns:
            Path: 処理後のパス
            
        Raises:
            FolderProcessorError: パス処理中のエラー
        """
        try:
            if str(path) == '.':
                return path

            # パス要素を分解して各フォルダ名を処理
            parts = path.parts
            processed_parts = []
            
            for part in parts:
                # フォルダ名の置換処理
                processed_name = self._process_name(part, replacements)
                processed_parts.append(processed_name)
            
            # 処理後のパスを生成
            processed_path = Path(*processed_parts)
            
            self.logger.debug(f"フォルダパス処理: {path} -> {processed_path}")
            return processed_path

        except Exception as e:
            self.logger.error(f"パス処理エラー {path}: {str(e)}")
            raise FolderProcessorError(f"パスの処理中にエラーが発生しました: {e}")

    def create_directory_structure(self, base_path: Path, relative_path: Path) -> Path:
        """
        ディレクトリ構造を作成
        
        Args:
            base_path: 基準となるパス
            relative_path: 作成する相対パス
            
        Returns:
            Path: 作成したディレクトリのパス
            
        Raises:
            FolderProcessorError: 出力先に既存のディレクトリが存在する場合
        """
        try:
            # 完全なパスを構築
            full_path = base_path / relative_path
            
            # 親ディレクトリも含めて、パス上の全てのディレクトリをチェック
            current_path = base_path
            for part in relative_path.parts:
                current_path = current_path / part
                if current_path.exists():
                    raise FolderProcessorError(f"出力先に既存のディレクトリが存在します: {current_path}")
            
            # バックアップディレクトリの準備（エラー時の復旧用）
            backup_dir = None
            if full_path.exists():
                backup_dir = full_path.parent / f"{full_path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.move(full_path, backup_dir)
            
            try:
                # ディレクトリを作成
                full_path.mkdir(parents=True)
                self._processed_paths.append(full_path)
                self.logger.info(f"ディレクトリを作成: {full_path}")
                
                # バックアップの削除
                if backup_dir and backup_dir.exists():
                    shutil.rmtree(backup_dir)
                
                return full_path
                
            except Exception as e:
                # エラー時の復旧処理
                if backup_dir and backup_dir.exists():
                    if full_path.exists():
                        shutil.rmtree(full_path)
                    shutil.move(backup_dir, full_path)
                raise FolderProcessorError(f"ディレクトリの作成に失敗しました: {e}")
                
        except FolderProcessorError:
            raise
        except Exception as e:
            self.logger.error(f"ディレクトリ構造作成エラー {relative_path}: {str(e)}")
            raise FolderProcessorError(f"ディレクトリ構造の作成中にエラーが発生しました: {e}")

    def rollback_created_directories(self) -> None:
        """作成したディレクトリを削除（エラー時のロールバック用）"""
        for path in reversed(self._processed_paths):
            try:
                if path.exists():
                    shutil.rmtree(path)
                    self.logger.info(f"ディレクトリを削除: {path}")
            except Exception as e:
                self.logger.error(f"ディレクトリ削除エラー {path}: {e}")
        self._processed_paths.clear()

    def sanitize_folder_name(self, name: str) -> str:
        """
        フォルダ名から不正な文字を除去
        
        Args:
            name: サニタイズするフォルダ名
            
        Returns:
            str: サニタイズされたフォルダ名
        """
        try:
            # Windowsでの禁止文字を置換
            sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
            # 先頭と末尾の空白とピリオドを除去
            sanitized = sanitized.strip(' .')
            # 空の場合はデフォルト名
            if not sanitized:
                sanitized = "unnamed"
            # 最大長の制限（255文字）
            if len(sanitized) > 255:
                sanitized = sanitized[:255]
            return sanitized
        except Exception as e:
            self.logger.error(f"フォルダ名サニタイズエラー {name}: {e}")
            return "unnamed"

    def _process_name(self, name: str, replacements: Dict[str, str]) -> str:
        """
        フォルダ名を処理
        
        Args:
            name: フォルダ名
            replacements: 置換ルール辞書
            
        Returns:
            str: 処理後のフォルダ名
        """
        try:
            processed_name = name
            for old_text, new_text in replacements.items():
                # 「なし」と「None」の場合は空文字列に置換
                if str(new_text).lower() in ['なし', 'none']:
                    processed_name = processed_name.replace(old_text, '')
                else:
                    processed_name = processed_name.replace(old_text, str(new_text))
                    
                self.logger.debug(f"フォルダ名置換: {name} -> {processed_name}")
            
            # 不正な文字を除去または置換
            processed_name = self.sanitize_folder_name(processed_name)
            return processed_name
            
        except Exception as e:
            self.logger.error(f"フォルダ名処理エラー {name}: {str(e)}")
            return name

    def __del__(self):
        """デストラクタ - 未処理のロールバックを実行"""
        try:
            if self._processed_paths:
                self.rollback_created_directories()
        except:
            pass