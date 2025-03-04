import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any

from ProjectManager.src.core.config import Config


class TaskLoader:
    def __init__(self, db_manager):
        """
        タスクローダーの初期化
        
        Args:
            db_manager: データベースマネージャーインスタンス
        """
        self.db_manager = db_manager
        
    def load_tasks(self) -> None:
        """
        全プロジェクトのタスクデータを読み込んでデータベースに登録
        """
        try:
            logging.info("タスクデータの読み込みを開始します")
            
            # 1. タスクテーブルのクリア
            self.db_manager.clear_tasks()
            logging.info("既存のタスクデータをクリアしました")
            
            all_tasks = []
            
            # 2. プロジェクト一覧を取得
            projects = self.db_manager.get_all_projects()
            logging.info(f"{len(projects)}件のプロジェクトを取得しました")
            
            # 3. 各プロジェクトのタスクを処理
            for project in projects:
                try:
                    # project_pathが設定されている場合はそのパスを使用
                    if project.get('project_path'):
                        project_dir = Path(project['project_path'])
                    else:
                        # 後方互換性のため、従来のパスも確認
                        project_dir = Config.OUTPUT_BASE_DIR / project['project_name']
                    
                    if not project_dir.exists():
                        logging.warning(f"プロジェクトディレクトリが存在しません: {project_dir}")
                        continue
                        
                    metadata_dir = project_dir / Config.METADATA_FOLDER_NAME
                    if not metadata_dir.exists():
                        logging.warning(f"メタデータディレクトリが存在しません: {metadata_dir}")
                        continue
                    
                    # CSVファイルの処理
                    tasks = self._process_project_csv_files(metadata_dir, project['project_name'])
                    all_tasks.extend(tasks)
                    
                except Exception as e:
                    logging.error(f"プロジェクト '{project['project_name']}' の処理中にエラーが発生: {e}")
                    continue
            
            # 4. タスクデータの一括登録
            if all_tasks:
                self.db_manager.insert_tasks(all_tasks)
                logging.info(f"合計 {len(all_tasks)} 件のタスクを読み込みました")
                
                # 5. ダッシュボードの更新
                self.db_manager.update_dashboard()
                logging.info("ダッシュボードテーブルを更新しました")
            else:
                logging.warning("読み込み可能なタスクデータが見つかりませんでした")
                
        except Exception as e:
            logging.error(f"タスクデータ読み込みエラー: {e}")
            raise
            
    def _process_project_csv_files(
        self, metadata_dir: Path, project_name: str
    ) -> List[Dict[str, Any]]:
        """
        プロジェクトのCSVファイルを処理
        
        Args:
            metadata_dir: メタデータディレクトリのパス
            project_name: プロジェクト名
            
        Returns:
            List[Dict[str, Any]]: 処理したタスクデータのリスト
        """
        tasks = []
        
        try:
            # CSVファイルの検索と処理
            csv_files = list(metadata_dir.glob('*.csv'))
            if not csv_files:
                logging.warning(f"CSVファイルが見つかりません: {metadata_dir}")
                return []

            for csv_file in csv_files:
                try:
                    # CSVファイルの読み込み（エンコーディングを試行）
                    df = None
                    last_error = None
                    for encoding in ['utf-8', 'utf-8-sig', 'cp932']:
                        try:
                            df = pd.read_csv(csv_file, encoding=encoding)
                            logging.info(f"CSVファイルを読み込みました: {csv_file} ({encoding})")
                            break
                        except UnicodeDecodeError as e:
                            last_error = e
                            continue
                    
                    if df is None:
                        logging.error(f"CSVファイルの読み込みに失敗: {csv_file}, エラー: {last_error}")
                        continue
                    
                    # 必要なカラムの存在確認
                    required_columns = [
                        'task_name', 'task_start_date', 'task_finish_date', 
                        'task_status', 'task_milestone'
                    ]
                    
                    # オプショナルなカラム
                    optional_columns = [
                        'task_assignee', 'task_work_hours'
                    ]
                    
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        logging.error(f"必要なカラムが不足しています: {csv_file}, "
                                    f"不足カラム: {', '.join(missing_columns)}")
                        continue
                    
                    # データの検証と変換
                    valid_statuses = ['未着手', '進行中', '完了', '中止']
                    row_count = 0
                    error_count = 0
                    
                    for index, row in df.iterrows():
                        row_count += 1
                        try:
                            # 必須フィールドの空値チェック
                            if any(pd.isna(row[col]) for col in required_columns):
                                logging.error(f"行 {index + 2}: 空値が含まれています")
                                error_count += 1
                                continue
                            
                            task = {
                                'task_name': str(row['task_name']).strip(),
                                'task_start_date': str(row['task_start_date']).strip(),
                                'task_finish_date': str(row['task_finish_date']).strip(),
                                'task_status': str(row['task_status']).strip(),
                                'task_milestone': str(row['task_milestone']).strip(),
                                'project_name': project_name
                            }
                            
                            # オプショナルフィールドの追加
                            # task_assignee (責任者)
                            if 'task_assignee' in df.columns and not pd.isna(row['task_assignee']):
                                task['task_assignee'] = str(row['task_assignee']).strip()
                            else:
                                task['task_assignee'] = ''
                                
                            # task_work_hours (予定工数)
                            if 'task_work_hours' in df.columns and not pd.isna(row['task_work_hours']):
                                try:
                                    task['task_work_hours'] = float(row['task_work_hours'])
                                except ValueError:
                                    task['task_work_hours'] = 0
                                    logging.warning(f"行 {index + 2}: 工数の値 '{row['task_work_hours']}' が数値に変換できず、0を設定しました")
                            else:
                                task['task_work_hours'] = 0
                            
                            # 空文字チェック (必須フィールドのみ)
                            if any(not task[key] for key in required_columns):
                                logging.error(f"行 {index + 2}: 空の値が含まれています")
                                error_count += 1
                                continue
                            
                            # ステータスの検証
                            if task['task_status'] not in valid_statuses:
                                logging.warning(f"行 {index + 2}: 無効なステータス '{task['task_status']}' を"
                                              f"'未着手' に置換します")
                                task['task_status'] = '未着手'
                            
                            # 日付形式の検証
                            try:
                                pd.to_datetime(task['task_start_date'])
                                pd.to_datetime(task['task_finish_date'])
                            except ValueError as e:
                                logging.error(f"行 {index + 2}: 日付形式が不正です: {e}")
                                error_count += 1
                                continue
                            
                            tasks.append(task)
                            
                        except Exception as e:
                            logging.error(f"行 {index + 2} の処理でエラーが発生: {e}")
                            error_count += 1
                            continue
                    
                    # 処理結果のサマリーを出力
                    logging.info(f"ファイル {csv_file} の処理完了: "
                               f"総行数 {row_count}, "
                               f"エラー {error_count}, "
                               f"処理成功 {row_count - error_count}")
                    
                except Exception as e:
                    logging.error(f"CSVファイル処理エラー {csv_file}: {e}")
                    continue
                    
            return tasks
            
        except Exception as e:
            logging.error(f"メタデータディレクトリ処理エラー {metadata_dir}: {e}")
            return []
            
    def validate_task_data(self, task: Dict[str, Any]) -> bool:
        """
        タスクデータの検証
        
        Args:
            task: 検証するタスクデータ
            
        Returns:
            bool: 検証結果（True: 成功、False: 失敗）
        """
        try:
            # 必須フィールドの存在確認
            required_fields = [
                'task_name', 'task_start_date', 'task_finish_date',
                'task_status', 'task_milestone', 'project_name'
            ]
            
            for field in required_fields:
                if field not in task or not task[field]:
                    logging.error(f"必須フィールド {field} が不足しています")
                    return False
            
            # データ型の検証
            try:
                pd.to_datetime(task['task_start_date'])
                pd.to_datetime(task['task_finish_date'])
            except ValueError as e:
                logging.error(f"日付形式が不正です: {e}")
                return False
            
            # ステータスの検証
            valid_statuses = ['未着手', '進行中', '完了', '中止']
            if task['task_status'] not in valid_statuses:
                logging.error(f"無効なステータスです: {task['task_status']}")
                return False
            
            # 工数のデータ型検証
            if 'task_work_hours' in task:
                try:
                    float(task['task_work_hours'])
                except ValueError:
                    logging.error(f"工数の値が数値ではありません: {task['task_work_hours']}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"タスクデータ検証エラー: {e}")
            return False