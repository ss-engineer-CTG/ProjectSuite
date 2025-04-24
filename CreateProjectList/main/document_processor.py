"""ドキュメント処理の制御クラス"""

from pathlib import Path
from typing import Dict, List, Optional, Type, Callable, Any
import logging
import shutil
import tempfile
import os
from datetime import datetime

from CreateProjectList.utils.config_manager import ConfigManager
from CreateProjectList.utils.db_context import DatabaseContext
from CreateProjectList.processors.folder_processor import FolderProcessor
from CreateProjectList.processors.document_processor_factory import DocumentProcessorFactory
from CreateProjectList.utils.log_manager import LogManager
from CreateProjectList.utils.path_manager import PathManager
from CreateProjectList.utils.path_constants import PathKeys

class DatabaseError(Exception):
    """データベース操作に関連するエラー"""
    pass

class ProcessingError(Exception):
    """文書処理に関連するエラー"""
    pass

class DocumentProcessor:
    """文書処理の制御クラス"""
    
    def __init__(self):
        """初期化"""
        # ロガーの初期化
        self.logger = LogManager().get_logger(__name__)
        
        # 内部変数の初期化
        self._replacement_rules = []
        self._config_manager = None
        self.folder_processor = FolderProcessor()
        self.processor_factory = DocumentProcessorFactory()
        self.db_context = None
        self.current_project_data = None
        self.temp_dir = None
        
        # PathRegistryの初期化
        try:
            from PathRegistry import PathRegistry
            self.registry = PathRegistry.get_instance()
        except ImportError:
            self.registry = None
            self.logger.warning("PathRegistryを読み込めませんでした")
        
        # 設定の初期化
        self._initialize_config()
        self._initialize_database()
        self._initialize_temp_dir()
        
        # 追加: 入力/出力フォルダを強制設定し、設定ファイルに保存
        try:
            if self.registry:
                paths_updated = False
                
                # 入力フォルダの強制設定
                pm_templates_dir = self.registry.get_path("PM_TEMPLATES_DIR")
                if pm_templates_dir:
                    self.last_input_folder = pm_templates_dir
                    self.logger.info(f"入力フォルダを強制的に設定: {pm_templates_dir}")
                    paths_updated = True
                
                # 出力フォルダの強制設定
                pm_projects_dir = self.registry.get_path("OUTPUT_BASE_DIR")
                if pm_projects_dir:
                    self.last_output_folder = pm_projects_dir
                    self.logger.info(f"出力フォルダを強制的に設定: {pm_projects_dir}")
                    paths_updated = True
                
                # 重要: 設定ファイルに明示的に保存（これが新しい部分）
                if paths_updated and self._config_manager:
                    # 設定ファイルの値を直接更新
                    self._config_manager.config['last_input_folder'] = pm_templates_dir
                    self._config_manager.config['last_output_folder'] = pm_projects_dir
                    
                    # 変更をファイルに書き込み
                    self._config_manager.save_config()
                    self.logger.info("設定ファイルにパス情報を保存しました")
        except Exception as e:
            self.logger.warning(f"フォルダパスの強制設定に失敗: {e}")

    def _initialize_config(self) -> None:
        """設定の初期化"""
        try:
            self._config_manager = ConfigManager()
            self._replacement_rules = self._config_manager.get_replacement_rules()
            self.logger.info("設定を初期化しました")
        except Exception as e:
            self.logger.error(f"設定初期化エラー: {e}")
            raise

    def _initialize_database(self) -> None:
        """データベースの初期化"""
        try:
            db_path = self._config_manager.get_db_path()
            if db_path:
                self.db_context = DatabaseContext(db_path)
                self.is_db_connected = self.db_context.test_connection()
                self.logger.info(f"データベースに接続しました: {db_path}")
            else:
                self.db_context = None
                self.is_db_connected = False
                self.logger.warning("データベースパスが設定されていません")
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
            self.db_context = None
            self.is_db_connected = False

    def _initialize_temp_dir(self) -> None:
        """一時ディレクトリの初期化"""
        try:
            # PathRegistryから一時ディレクトリを取得
            if self.registry:
                registry_temp_dir = self.registry.get_path(PathKeys.CPL_TEMP_DIR)
                if registry_temp_dir:
                    temp_path = Path(registry_temp_dir)
                    temp_path.mkdir(parents=True, exist_ok=True)
                    self.temp_dir = temp_path
                    self.logger.info(f"PathRegistryから一時ディレクトリを設定: {self.temp_dir}")
                    return
            
            # ユーザードキュメント内の一時ディレクトリを使用
            user_temp_dir = PathManager.get_user_directory() / "CreateProjectList" / "temp"
            
            # ディレクトリ作成
            try:
                user_temp_dir.mkdir(parents=True, exist_ok=True)
                self.temp_dir = user_temp_dir
                self.logger.info(f"一時ディレクトリを作成しました: {self.temp_dir}")
            except PermissionError:
                # 権限エラーの場合はシステム一時ディレクトリを使用
                self.temp_dir = Path(tempfile.mkdtemp(prefix="doc_processor_"))
                self.logger.warning(f"権限エラーのため、システム一時ディレクトリを使用: {self.temp_dir}")
            
            # 設定マネージャーに保存
            if self._config_manager:
                self._config_manager.config['temp_dir'] = str(self.temp_dir)
                self._config_manager.save_config()
            
        except Exception as e:
            self.logger.error(f"一時ディレクトリ作成エラー: {e}")
            # フォールバックとしてsys.tempを使用
            self.temp_dir = Path(tempfile.mkdtemp(prefix="doc_processor_"))
            self.logger.info(f"フォールバック一時ディレクトリを作成: {self.temp_dir}")

    def cleanup_temp_files(self) -> None:
        """一時ファイルのクリーンアップ"""
        try:
            if self.temp_dir:
                # 一時ディレクトリ内のファイルだけを削除（ディレクトリは保持）
                for item in self.temp_dir.glob('*'):
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                self.logger.info(f"一時ディレクトリをクリーンアップしました: {self.temp_dir}")
        except Exception as e:
            self.logger.error(f"一時ファイルのクリーンアップエラー: {e}")

    def set_project_data(self, project_data: Dict[str, Any]) -> None:
        """
        プロジェクトデータを設定
        
        Args:
            project_data: ProjectManagerから渡されるプロジェクトデータ
        """
        try:
            self.current_project_data = project_data
            self.logger.info(f"プロジェクトデータを設定: {project_data['project_name']}")
        except Exception as e:
            self.logger.error(f"プロジェクトデータ設定エラー: {e}")
            raise

    def process_documents(self, input_folder_path: str, output_folder_path: str, 
                        progress_callback: Optional[Callable] = None, 
                        cancel_check: Optional[Callable] = None) -> Dict:
        """
        フォルダ内のドキュメントを処理
        
        Args:
            input_folder_path: 入力フォルダのパス
            output_folder_path: 出力フォルダのパス
            progress_callback: 進捗報告コールバック
            cancel_check: キャンセルチェックコールバック
        
        Returns:
            Dict: {
                'processed': List[Path],  # 処理成功したファイルリスト
                'errors': List[Tuple[Path, str]],  # エラーが発生したファイルとエラーメッセージ
                'cancelled': bool  # キャンセルされたかどうか
            }
        
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
        """
        if not self.current_project_data:
            raise ProcessingError("プロジェクトが選択されていません")

        input_path = Path(input_folder_path)
        output_path = Path(output_folder_path)
        
        try:
            # フォルダの基本検証
            self._validate_folders(input_path, output_path)

            # 内部用のコールバックを保存
            self._progress_callback = progress_callback
            self._cancel_check = cancel_check
            
            # 出力先の検証
            if progress_callback:
                progress_callback(0, "出力先をチェック中...", "")

            is_valid, existing_items = self.folder_processor.validate_output_location(input_path, output_path)
            if not is_valid:
                error_message = "出力先に既存のファイルまたはフォルダが存在します:\n"
                for item in existing_items[:5]:  # 最初の5件のみ表示
                    error_message += f"- {item}\n"
                if len(existing_items) > 5:
                    error_message += f"...他 {len(existing_items) - 5} 件"
                raise ProcessingError(error_message)

            # キャンセルチェック
            if cancel_check and cancel_check():
                return {
                    'processed': [],
                    'errors': [],
                    'cancelled': True
                }

            # 置換ルールを辞書形式に変換
            replacements = self._create_replacement_dict()

            if progress_callback:
                progress_callback(10, "フォルダ構造をチェック中...", "")

            # フォルダ構造の作成
            try:
                folders = self._create_folder_structure(
                    input_path, 
                    output_path,
                    replacements,
                    progress_callback
                )
            except Exception as e:
                raise ProcessingError(f"フォルダ構造の作成に失敗しました: {str(e)}")

            # キャンセルチェック
            if cancel_check and cancel_check():
                # フォルダ構造をロールバック
                self.folder_processor.rollback_created_directories()
                return {
                    'processed': [],
                    'errors': [],
                    'cancelled': True
                }

            # 処理対象ファイルの取得
            files = self._get_target_files(input_path)
            if not files:
                self.logger.info("処理対象ファイルは見つかりませんでした")
                return {
                    'processed': [],
                    'errors': [],
                    'cancelled': False
                }

            # ファイルの処理
            processed_files = []
            errors = []
            try:
                processed_files, errors = self._process_files(
                    files,
                    input_path,
                    output_path,
                    replacements,
                    progress_callback,
                    cancel_check
                )

                # エラーが発生した場合でも処理済みファイルの情報は返す
                return {
                    'processed': processed_files,
                    'errors': errors,
                    'cancelled': False
                }

            except Exception as e:
                # ファイル処理中のエラー
                if processed_files:  # 一部のファイルは処理済み
                    return {
                        'processed': processed_files,
                        'errors': errors + [(None, str(e))],
                        'cancelled': False
                    }
                else:  # 全てのファイルで処理失敗
                    raise ProcessingError(f"ファイル処理に失敗しました: {str(e)}")

        except Exception as e:
            self.logger.error(f"ドキュメント処理エラー: {e}")
            # フォルダ構造をロールバック（もし作成されていれば）
            try:
                self.folder_processor.rollback_created_directories()
            except Exception as rollback_error:
                self.logger.error(f"ロールバック中にエラーが発生: {rollback_error}")
            raise ProcessingError(f"ドキュメント処理エラー: {e}")

        finally:
            # 一時ファイルのクリーンアップ
            self.cleanup_temp_files()
            
            # 進捗表示を完了状態に
            if progress_callback:
                try:
                    progress_callback(100, "処理完了", "")
                except Exception as e:
                    self.logger.error(f"進捗表示の更新に失敗: {e}")

    def _validate_folders(self, input_path: Path, output_path: Path) -> None:
        """
        フォルダの妥当性チェック
        
        Args:
            input_path: 入力フォルダパス
            output_path: 出力フォルダパス
        """
        if not input_path.exists():
            raise ValueError("入力フォルダが存在しません")
        if not input_path.is_dir():
            raise ValueError("入力パスがフォルダではありません")
        if not any(input_path.iterdir()):
            raise ValueError("入力フォルダが空です")
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True)
            except Exception as e:
                raise ValueError(f"出力フォルダの作成に失敗しました: {e}")

    def _generate_project_folder_name(self) -> str:
        """
        プロジェクトフォルダ名の生成
        
        Returns:
            str: フォルダ名
        """
        folder_components = [
            str(self.current_project_data.get(key, ''))
            for key in ['division', 'factory', 'process', 'line']
        ]
        folder_components.extend([
            self.current_project_data['project_name'],
            datetime.now().strftime('%Y-%m-%d'),
            self.current_project_data['manager']
        ])
        
        # 空の値を除外
        folder_components = [c for c in folder_components if c]
        
        # フォルダ名を生成
        folder_name = '_'.join(folder_components)
        
        # 不正な文字を除去
        folder_name = self.folder_processor.sanitize_folder_name(folder_name)
        
        return folder_name

    def _create_replacement_dict(self) -> Dict[str, str]:
        """
        置換ルール辞書の作成
        
        Returns:
            Dict[str, str]: 置換ルール辞書
        """
        replacements = {}
        for rule in self._replacement_rules:
            value = str(self.current_project_data.get(rule['replace'], ''))
            if value.lower() in ['なし', 'none', '']:
                value = ''
            replacements[rule['search']] = value
        return replacements

    def _create_folder_structure(self,
                               input_path: Path,
                               output_path: Path,
                               replacements: Dict[str, str],
                               progress_callback: Optional[Callable] = None) -> List[Path]:
        """
        フォルダ構造の作成
        
        Args:
            input_path: 入力フォルダパス
            output_path: 出力フォルダパス
            replacements: 置換ルール辞書
            progress_callback: 進捗コールバック
            
        Returns:
            List[Path]: 作成したフォルダのリスト
        """
        created_folders = []
        try:
            folders = [f for f in input_path.rglob('*') if f.is_dir()]
            total_folders = len(folders)
            
            for i, folder in enumerate(folders, 1):
                try:
                    relative_path = folder.relative_to(input_path)
                    processed_path = self.folder_processor.process_path(
                        relative_path,
                        replacements
                    )
                    target_path = output_path / processed_path
                    target_path.mkdir(parents=True, exist_ok=True)
                    created_folders.append(target_path)
                    
                    if progress_callback:
                        progress = (i / total_folders) * 20
                        progress_callback(
                            progress,
                            f"フォルダ処理中 ({i}/{total_folders})",
                            str(relative_path)
                        )
                        
                except Exception as e:
                    self.logger.error(f"フォルダ作成エラー {folder}: {e}")
                    raise
                    
            return created_folders
            
        except Exception as e:
            self.logger.error(f"フォルダ構造作成エラー: {e}")
            raise

    def _get_target_files(self, folder_path: Path) -> List[Path]:
        """
        処理対象ファイルの取得
        
        Args:
            folder_path: フォルダパス
            
        Returns:
            List[Path]: 処理対象ファイルのリスト
        """
        files = []
        supported_extensions = self.processor_factory.get_supported_extensions()
        
        for file_path in folder_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                files.append(file_path)
        return files

    def _process_files(self,
                      files: List[Path],
                      input_root: Path,
                      output_root: Path,
                      replacements: Dict[str, str],
                      progress_callback: Optional[Callable] = None,
                      cancel_check: Optional[Callable] = None) -> tuple:
        """
        ファイルの一括処理
        
        Args:
            files: 処理対象ファイルのリスト
            input_root: 入力ルートパス
            output_root: 出力ルートパス
            replacements: 置換ルール辞書
            progress_callback: 進捗コールバック
            cancel_check: キャンセルチェックコールバック
            
        Returns:
            tuple: (処理成功ファイルリスト, エラーリスト)
        """
        processed_files = []
        errors = []
        total_files = len(files)
        
        for i, file_path in enumerate(files, 1):
            if cancel_check and cancel_check():
                break
                
            try:
                if progress_callback:
                    progress = 20 + ((i / total_files) * 80)
                    progress_callback(
                        progress,
                        f"ファイル処理中 ({i}/{total_files})",
                        str(file_path.name)
                    )
                    
                self._process_single_file(
                    file_path,
                    input_root,
                    output_root,
                    replacements
                )
                processed_files.append(file_path)
                
            except Exception as e:
                self.logger.error(f"ファイル処理エラー {file_path}: {e}")
                errors.append((file_path, str(e)))
                
        return processed_files, errors

    def _process_single_file(self,
                           file_path: Path,
                           input_root: Path,
                           output_root: Path,
                           replacements: Dict[str, str]) -> None:
        """
        単一ファイルの処理
        
        Args:
            file_path: 処理対象ファイル
            input_root: 入力ルートパス
            output_root: 出力ルートパス
            replacements: 置換ルール辞書
        """
        # 適切なプロセッサーを取得
        processor = self.processor_factory.create_processor(file_path)
        if not processor:
            raise ProcessingError(f"未対応のファイル形式です: {file_path}")
        
        # プロセッサーにコールバックを設定
        if hasattr(processor, 'set_progress_callback'):
            processor.set_progress_callback(self._progress_callback)
        if hasattr(processor, 'set_cancel_check'):
            processor.set_cancel_check(self._cancel_check)
        
        # 出力パスの生成
        relative_path = file_path.relative_to(input_root)
        processed_path = self.folder_processor.process_path(
            relative_path.parent,
            replacements
        )
        
        # ファイル名の処理
        new_name = self.folder_processor._process_name(relative_path.name, replacements)
        
        # 最終的な出力パス
        output_path = output_root / processed_path / new_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # バックアップを作成
        backup_path = self._create_backup(file_path)
        
        try:
            # ファイル処理の実行
            processor.process_file(file_path, output_path, replacements)
            self.logger.info(f"ファイル処理成功: {file_path} -> {output_path}")
            
        except Exception as e:
            self._restore_from_backup(backup_path, file_path)
            raise ProcessingError(f"ファイル処理エラー: {str(e)}")
            
        finally:
            if backup_path and backup_path.exists():
                backup_path.unlink()

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """
        バックアップファイルを作成
        
        Args:
            file_path: バックアップ対象のファイル
            
        Returns:
            Optional[Path]: バックアップファイルのパス
        """
        try:
            # 一時ディレクトリにバックアップを作成
            backup_path = self.temp_dir / f"{file_path.name}.bak"
            shutil.copy2(file_path, backup_path)
            self.logger.debug(f"バックアップ作成: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー {file_path}: {e}")
            return None

    def _restore_from_backup(self, backup_path: Optional[Path], original_path: Path) -> None:
        """
        バックアップからファイルを復元
        
        Args:
            backup_path: バックアップファイルのパス
            original_path: 復元先の元のファイルパス
        """
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, original_path)
                self.logger.info(f"バックアップから復元: {backup_path} -> {original_path}")
            except Exception as e:
                self.logger.error(f"バックアップ復元エラー: {e}")

    @property
    def config_manager(self) -> ConfigManager:
        """設定マネージャーを取得"""
        if self._config_manager is None:
            self._initialize_config()
        return self._config_manager

    @property
    def replacement_rules(self) -> List[Dict[str, str]]:
        """置換ルールを取得"""
        return self._replacement_rules

    @replacement_rules.setter
    def replacement_rules(self, value: List[Dict[str, str]]) -> None:
        """置換ルールを設定"""
        try:
            self._replacement_rules = value
            if self._config_manager:
                self._config_manager.set_replacement_rules(value)
            self.logger.info("置換ルールを更新しました")
        except Exception as e:
            self.logger.error(f"置換ルール設定エラー: {e}")
            raise

    @property
    def db_path(self) -> str:
        """データベースパスを取得"""
        return self.config_manager.get_db_path()
    
    @db_path.setter
    def db_path(self, value: str) -> None:
        """データベースパスを設定"""
        try:
            self.config_manager.set_db_path(value)
            self._initialize_database()
            self.logger.info(f"データベースパスを更新: {value}")
        except Exception as e:
            self.logger.error(f"データベースパス設定エラー: {e}")
            raise DatabaseError(f"データベースパスの設定に失敗: {str(e)}")
    
    @property
    def last_input_folder(self) -> str:
        """最後に使用した入力フォルダを取得"""
        return self.config_manager.get_input_folder()
    
    @last_input_folder.setter
    def last_input_folder(self, value: str) -> None:
        """最後に使用した入力フォルダを設定"""
        self.config_manager.set_input_folder(value)
        self.logger.debug(f"入力フォルダを更新: {value}")
    
    @property
    def last_output_folder(self) -> str:
        """最後に使用した出力フォルダを取得"""
        return self.config_manager.get_output_folder()
    
    @last_output_folder.setter
    def last_output_folder(self, value: str) -> None:
        """最後に使用した出力フォルダを設定"""
        self.config_manager.set_output_folder(value)
        self.logger.debug(f"出力フォルダを更新: {value}")

    def __del__(self):
        """デストラクタ - リソースのクリーンアップ"""
        try:
            self.cleanup_temp_files()
        except:
            pass  # デストラクタ内でのエラーは無視