"""
プロジェクト移行用ユーティリティ
既存のプロジェクトをデスクトップに移行する機能を提供
"""

import os
import sys
import logging
import sqlite3
import shutil
import traceback
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime

class ProjectMigrator:
    """
    プロジェクト移行を担当するクラス
    現在のPROJECT_DIRから新しいOUTPUT_BASE_DIRへのプロジェクト移行処理を提供
    """
    
    def __init__(self, target_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            target_dir: 移行先のディレクトリパス。指定しない場合はデスクトップに作成
        """
        # ロガー設定
        self.logger = logging.getLogger(__name__)
        
        # 移行元と移行先パスの設定
        self.source_dir = Path.home() / "Documents" / "ProjectSuite" / "ProjectManager" / "data" / "projects"
        
        if target_dir is None:
            self.target_dir = Path.home() / "Desktop" / "projects"
        else:
            self.target_dir = Path(target_dir)
            
        # PathRegistryの取得
        try:
            from PathRegistry import PathRegistry
            self.registry = PathRegistry.get_instance()
        except ImportError:
            self.registry = None
            self.logger.warning("PathRegistryをインポートできません。レジストリ機能は使用できません。")
    
    def check_source_target(self) -> Tuple[bool, str]:
        """
        移行元と移行先の状態をチェック
        
        Returns:
            Tuple[bool, str]: (チェック結果, メッセージ)
        """
        # 移行元の存在確認
        if not self.source_dir.exists() or not self.source_dir.is_dir():
            return False, f"移行元ディレクトリが存在しません: {self.source_dir}"
            
        # 移行元に内容があるか確認
        source_items = list(self.source_dir.glob("*"))
        if not source_items:
            return False, f"移行元ディレクトリが空です: {self.source_dir}"
            
        # 移行先ディレクトリの作成
        if not self.target_dir.exists():
            try:
                self.target_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"移行先ディレクトリを作成しました: {self.target_dir}")
            except Exception as e:
                return False, f"移行先ディレクトリの作成に失敗しました: {e}"
                
        # 移行先に書き込み権限があるか確認
        try:
            test_file = self.target_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            return False, f"移行先への書き込み権限がありません: {e}"
            
        return True, "移行元と移行先のチェックが完了しました"
    
    def migrate_projects(self, overwrite: bool = False) -> Dict[str, Any]:
        """
        プロジェクトの移行を実行
        
        Args:
            overwrite: 同名ファイルを上書きするかどうか
            
        Returns:
            Dict[str, Any]: 移行結果の情報
        """
        result = {
            "success": False,
            "total_projects": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": [],
            "migrated_projects": [],
            "skipped_projects": [],
            "db_updated": False
        }
        
        try:
            # 移行元と移行先のチェック
            check_result, message = self.check_source_target()
            if not check_result:
                result["errors"].append(message)
                return result
                
            # プロジェクトフォルダのリストを取得
            project_folders = [item for item in self.source_dir.iterdir() if item.is_dir()]
            result["total_projects"] = len(project_folders)
            
            # 一つずつ移行
            for folder in project_folders:
                try:
                    dest_folder = self.target_dir / folder.name
                    
                    # 同名フォルダが既に存在するかチェック
                    if dest_folder.exists():
                        if overwrite:
                            # 上書きオプションが有効なら、既存フォルダを削除
                            shutil.rmtree(dest_folder)
                            self.logger.info(f"既存の移行先フォルダを削除: {dest_folder}")
                        else:
                            # 上書きしない場合はスキップ
                            self.logger.warning(f"同名のフォルダが既に存在するためスキップ: {dest_folder}")
                            result["skipped"] += 1
                            result["skipped_projects"].append(str(folder.name))
                            continue
                    
                    # フォルダをコピー
                    shutil.copytree(folder, dest_folder)
                    self.logger.info(f"プロジェクトフォルダを移行: {folder} -> {dest_folder}")
                    
                    result["migrated"] += 1
                    result["migrated_projects"].append(str(folder.name))
                    
                except Exception as e:
                    error_msg = f"プロジェクト '{folder.name}' の移行中にエラー: {e}"
                    self.logger.error(error_msg)
                    result["errors"].append(error_msg)
            
            # データベースのパス参照を更新
            db_result = self.update_database_paths()
            result["db_updated"] = db_result["success"]
            if not db_result["success"]:
                result["errors"].extend(db_result["errors"])
            
            # 移行成功判定
            result["success"] = result["migrated"] > 0 and (len(result["errors"]) == 0 or result["db_updated"])
            
            return result
            
        except Exception as e:
            error_msg = f"プロジェクト移行処理でエラーが発生: {e}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
            return result
    
    def update_database_paths(self) -> Dict[str, Any]:
        """
        データベース内のプロジェクトパスを更新
        
        Returns:
            Dict[str, Any]: 更新結果
        """
        result = {
            "success": False,
            "updated_count": 0,
            "errors": []
        }
        
        conn = None
        try:
            # データベースのパスを取得
            if self.registry:
                db_path = self.registry.get_path("DB_PATH")
            else:
                db_path = str(Path.home() / "Documents" / "ProjectSuite" / "ProjectManager" / "data" / "projects.db")
            
            # データベースの存在確認
            if not Path(db_path).exists():
                result["errors"].append(f"データベースファイルが見つかりません: {db_path}")
                return result
            
            # データベースに接続
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 更新に使用するパスパターン
            old_path_pattern = str(self.source_dir)
            new_path_pattern = str(self.target_dir)
            
            # プロジェクトパスの更新
            cursor.execute(
                "UPDATE projects SET project_path = REPLACE(project_path, ?, ?) WHERE project_path LIKE ?",
                (old_path_pattern, new_path_pattern, f"{old_path_pattern}%")
            )
            project_count = cursor.rowcount
            
            # ガントチャートパスの更新
            cursor.execute(
                "UPDATE projects SET ganttchart_path = REPLACE(ganttchart_path, ?, ?) WHERE ganttchart_path LIKE ?",
                (old_path_pattern, new_path_pattern, f"{old_path_pattern}%")
            )
            gantt_count = cursor.rowcount
            
            # 変更を確定
            conn.commit()
            
            result["success"] = True
            result["updated_count"] = project_count + gantt_count
            self.logger.info(f"データベース内のパス参照を更新: プロジェクト {project_count}件, ガントチャート {gantt_count}件")
            
            return result
            
        except Exception as e:
            error_msg = f"データベース更新エラー: {e}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
            
            # ロールバック
            if conn:
                conn.rollback()
                
            return result
            
        finally:
            # 接続のクローズ
            if conn:
                conn.close()
    
    def backup_source_dir(self) -> Tuple[bool, str]:
        """
        移行元ディレクトリのバックアップを作成
        
        Returns:
            Tuple[bool, str]: (成功したか, メッセージ)
        """
        try:
            # バックアップディレクトリの作成
            backup_dir = Path.home() / "Documents" / "ProjectSuite" / "backup" / "projects"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # タイムスタンプを含むバックアップフォルダ名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"projects_backup_{timestamp}"
            
            # バックアップの作成
            shutil.copytree(self.source_dir, backup_path)
            
            self.logger.info(f"プロジェクトフォルダのバックアップを作成: {backup_path}")
            return True, f"バックアップを作成しました: {backup_path}"
            
        except Exception as e:
            error_msg = f"バックアップ作成エラー: {e}"
            self.logger.error(error_msg)
            return False, error_msg
            
    @staticmethod
    def run_migration(target_dir: Optional[str] = None, backup: bool = True, overwrite: bool = False) -> Dict[str, Any]:
        """
        静的メソッド: 移行処理を実行
        
        Args:
            target_dir: 移行先ディレクトリ（デフォルトはデスクトップのprojects）
            backup: バックアップを作成するかどうか
            overwrite: 同名ファイルを上書きするかどうか
            
        Returns:
            Dict[str, Any]: 移行結果
        """
        migrator = ProjectMigrator(target_dir)
        
        if backup:
            backup_success, backup_message = migrator.backup_source_dir()
            if not backup_success:
                return {
                    "success": False,
                    "message": f"バックアップの作成に失敗しました: {backup_message}",
                    "errors": [backup_message]
                }
        
        # 移行の実行
        result = migrator.migrate_projects(overwrite)
        
        # 結果メッセージの作成
        if result["success"]:
            result["message"] = (
                f"移行成功: {result['migrated']}件のプロジェクトを移行しました"
                f"{' (バックアップあり)' if backup else ''}"
            )
        else:
            result["message"] = (
                f"移行に問題が発生: {result['migrated']}件移行, "
                f"{result['skipped']}件スキップ, {len(result['errors'])}件のエラー"
            )
            
        return result

# コマンドラインから実行可能にする
if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("project_migration.log"),
            logging.StreamHandler()
        ]
    )
    
    print("ProjectSuiteプロジェクト移行ユーティリティ")
    print("==========================================")
    print("このツールはProjectManagerのプロジェクトをデスクトップに移行します。")
    
    try:
        # コマンドライン引数のパース
        import argparse
        parser = argparse.ArgumentParser(description='プロジェクト移行ツール')
        parser.add_argument(
            '--target', 
            help='移行先ディレクトリ (デフォルト: デスクトップ/projects)'
        )
        parser.add_argument(
            '--no-backup', 
            action='store_true', 
            help='バックアップを作成しない'
        )
        parser.add_argument(
            '--overwrite', 
            action='store_true', 
            help='同名のファイルが存在する場合に上書きする'
        )
        args = parser.parse_args()
        
        # 移行の実行
        result = ProjectMigrator.run_migration(
            target_dir=args.target,
            backup=not args.no_backup,
            overwrite=args.overwrite
        )
        
        # 結果の表示
        if result["success"]:
            print("\n✅ 移行成功!")
            print(f"移行したプロジェクト: {result['migrated']}件")
            if result.get("skipped", 0) > 0:
                print(f"スキップしたプロジェクト: {result['skipped']}件")
            print(f"データベース更新: {'成功' if result.get('db_updated', False) else '失敗'}")
        else:
            print("\n❌ 移行に問題が発生しました")
            print(f"移行したプロジェクト: {result.get('migrated', 0)}件")
            print(f"スキップしたプロジェクト: {result.get('skipped', 0)}件")
            print("エラー:")
            for error in result.get("errors", []):
                print(f"- {error}")
        
        print("\n移行の詳細はproject_migration.logファイルを確認してください。")
        
    except Exception as e:
        print(f"\n❌ 予期せぬエラーが発生しました: {e}")
        traceback.print_exc()
        sys.exit(1)