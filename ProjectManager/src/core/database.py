import re
import os
import shutil
import sqlite3
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from ProjectManager.src.core.config import Config

class DatabaseManager:
    def __init__(self, db_path: Path):
        """
        データベースマネージャーの初期化
        
        Args:
            db_path (Path): データベースファイルのパス
        """
        self.db_path = db_path
        self.setup_database()
        
    def _get_connection(self) -> sqlite3.Connection:
        """
        データベース接続を取得
        
        Returns:
            sqlite3.Connection: データベース接続オブジェクト
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def setup_database(self):
        """データベースとテーブルの初期設定"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # プロジェクトテーブルのセットアップ
            self._setup_projects_table(cursor)
            
            # タスクテーブルのセットアップ
            self._setup_tasks_table(cursor)
            
            # ダッシュボードテーブルのセットアップ
            self._setup_dashboard_table(cursor)
            
            # タスクテーブルのマイグレーション
            self._migrate_tasks_table(cursor)
            
            conn.commit()
            logging.info("データベースの初期設定が完了しました")
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logging.error(f"データベース設定エラー: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _setup_projects_table(self, cursor):
        """プロジェクトテーブルの設定"""
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='projects'
        """)
        
        if cursor.fetchone() is None:
            cursor.execute('''
                CREATE TABLE projects (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL UNIQUE,
                    start_date TEXT NOT NULL,
                    manager TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    approver TEXT NOT NULL,
                    division TEXT,
                    factory TEXT,
                    process TEXT,
                    line TEXT,
                    status TEXT NOT NULL DEFAULT '進行中' CHECK(status IN ('進行中', '完了', '中止')),
                    project_path TEXT,
                    ganttchart_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            logging.info("projectsテーブルを作成しました")
        else:
            # project_path列が存在するか確認
            cursor.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'project_path' not in columns:
                cursor.execute('ALTER TABLE projects ADD COLUMN project_path TEXT')
                logging.info("projectsテーブルにproject_path列を追加しました")
            
            # 既存のマイグレーションも実行
            self._check_and_migrate_projects_table(cursor)

    def _setup_tasks_table(self, cursor):
        """タスクテーブルの設定"""
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='tasks'
        """)
        
        if cursor.fetchone() is None:
            cursor.execute('''
                CREATE TABLE tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    task_start_date TEXT NOT NULL,
                    task_finish_date TEXT NOT NULL,
                    task_status TEXT NOT NULL CHECK(task_status IN ('未着手', '進行中', '完了', '中止')),
                    task_milestone TEXT NOT NULL,
                    task_assignee TEXT,
                    task_work_hours REAL,
                    project_name TEXT NOT NULL,
                    FOREIGN KEY (project_name) REFERENCES projects(project_name)
                        ON UPDATE CASCADE
                        ON DELETE CASCADE
                )
            ''')
            logging.info("tasksテーブルを作成しました")

    def _setup_dashboard_table(self, cursor):
        """ダッシュボードテーブルの設定"""
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='dashboard'
        """)
        
        if cursor.fetchone() is None:
            cursor.execute('''
                CREATE TABLE dashboard (
                    project_id INTEGER,
                    project_name TEXT,
                    manager TEXT,
                    division TEXT,
                    factory TEXT,
                    process TEXT,
                    line TEXT,
                    status TEXT,
                    created_at TEXT,
                    task_id INTEGER,
                    task_name TEXT,
                    task_start_date TEXT,
                    task_finish_date TEXT,
                    task_status TEXT,
                    task_milestone TEXT,
                    task_assignee TEXT,
                    task_work_hours REAL
                )
            ''')
            logging.info("dashboardテーブルを作成しました")

    def _migrate_tasks_table(self, cursor):
        """tasksテーブルのマイグレーション"""
        try:
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # task_milestone列がない場合はテーブルを再作成
            if 'task_milestone' not in columns:
                cursor.execute('''
                    CREATE TABLE tasks_temp (
                        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_name TEXT NOT NULL,
                        task_start_date TEXT NOT NULL,
                        task_finish_date TEXT NOT NULL,
                        task_status TEXT NOT NULL CHECK(task_status IN ('未着手', '進行中', '完了', '中止')),
                        task_milestone TEXT NOT NULL,
                        task_assignee TEXT,
                        task_work_hours REAL,
                        project_name TEXT NOT NULL,
                        FOREIGN KEY (project_name) REFERENCES projects(project_name)
                            ON UPDATE CASCADE
                            ON DELETE CASCADE
                    )
                ''')
                
                cursor.execute('''
                    INSERT INTO tasks_temp (
                        task_id, task_name, task_start_date, task_finish_date,
                        task_status, task_milestone, task_assignee, task_work_hours, project_name
                    )
                    SELECT 
                        task_id, task_name, task_start_date, task_finish_date,
                        task_status, '未設定' as task_milestone, '' as task_assignee, 0 as task_work_hours, project_name
                    FROM tasks
                ''')
                
                cursor.execute('DROP TABLE tasks')
                cursor.execute('ALTER TABLE tasks_temp RENAME TO tasks')
                
                logging.info("tasksテーブルのマイグレーションが完了しました")
            
            # 新しいカラムの追加
            else:
                # task_assignee列がなければ追加
                if 'task_assignee' not in columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN task_assignee TEXT')
                    logging.info("tasksテーブルにtask_assignee列を追加しました")
                
                # task_work_hours列がなければ追加
                if 'task_work_hours' not in columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN task_work_hours REAL')
                    logging.info("tasksテーブルにtask_work_hours列を追加しました")
                
        except Exception as e:
            logging.error(f"タスクテーブルのマイグレーションでエラーが発生: {e}")
            raise

    def _check_and_migrate_projects_table(self, cursor):
        """プロジェクトテーブルの構造確認とマイグレーション"""
        cursor.execute("PRAGMA table_info(projects)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # ganttchart_path列の追加
        if 'ganttchart_path' not in columns:
            try:
                cursor.execute('ALTER TABLE projects ADD COLUMN ganttchart_path TEXT')
                logging.info("projectsテーブルにganttchart_path列を追加しました")
            except sqlite3.Error as e:
                logging.error(f"ganttchart_path列の追加に失敗: {e}")
                raise
        
        if 'id' in columns and 'project_id' not in columns:
            logging.info("テーブルのマイグレーションを開始します")
            
            cursor.execute('''
                CREATE TABLE projects_temp (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL UNIQUE,
                    start_date TEXT NOT NULL,
                    manager TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    approver TEXT NOT NULL,
                    division TEXT,
                    factory TEXT,
                    process TEXT,
                    line TEXT,
                    status TEXT NOT NULL DEFAULT '進行中' CHECK(status IN ('進行中', '完了', '中止')),
                    project_path TEXT,
                    ganttchart_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                INSERT INTO projects_temp 
                SELECT 
                    id as project_id,
                    project_name,
                    start_date,
                    manager,
                    reviewer,
                    approver,
                    division,
                    factory,
                    process,
                    line,
                    status,
                    NULL as project_path,
                    NULL as ganttchart_path,
                    created_at,
                    updated_at
                FROM projects
            ''')
            
            cursor.execute('DROP TABLE projects')
            cursor.execute('ALTER TABLE projects_temp RENAME TO projects')
            
            logging.info("テーブルのマイグレーションが完了しました")

    def insert_project(self, project_data: Dict[str, Any]) -> int:
        """
        新規プロジェクトの登録
        
        Args:
            project_data: プロジェクトデータ
            
        Returns:
            int: 生成されたプロジェクトID
        """
        conn = None
        project_id = None
        try:
            # 1. プロジェクト情報の登録
            conn = self._get_connection()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO projects (
                    project_name, start_date, manager, reviewer, approver,
                    division, factory, process, line, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_data['project_name'],
                project_data['start_date'],
                project_data['manager'],
                project_data['reviewer'],
                project_data['approver'],
                project_data['division'],
                project_data['factory'],
                project_data['process'],
                project_data['line'],
                current_time,
                current_time
            ))
            
            project_id = cursor.lastrowid
            conn.commit()
            conn.close()
            conn = None
            
            # 2. プロジェクトフォルダの作成
            project_folder = self._create_project_folder(project_data)
            
            # 3. プロジェクトパスの更新
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE projects SET project_path = ? WHERE project_id = ?',
                (str(project_folder), project_id)
            )
            conn.commit()
            conn.close()
            conn = None
            
            # 4. ダッシュボードの更新
            self.update_dashboard()
            
            return project_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"プロジェクト登録エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def _create_project_folder(self, project_data: Dict[str, Any]) -> Path:
        """
        プロジェクトフォルダを作成
        
        Args:
            project_data: プロジェクトデータ
            
        Returns:
            Path: 作成したフォルダのパス
        """
        try:
            # フォルダ名の生成
            folder_components = [
                str(project_data.get(key, '')) for key in ['division', 'factory', 'process', 'line']
            ]
            folder_components.extend([
                project_data['project_name'],
                project_data['start_date'],
                project_data['manager']
            ])
            
            # 空の値を除外し、フォルダ名を生成
            folder_name = '_'.join(filter(None, folder_components))
            folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
            
            # 出力先ディレクトリの取得（動的に解決）
            output_base_dir = Config.get_output_base_dir()
            project_folder = output_base_dir / folder_name
            
            # フォルダが既に存在する場合は連番を付与
            base_folder_name = folder_name
            counter = 1
            while project_folder.exists():
                folder_name = f"{base_folder_name}_{counter}"
                project_folder = output_base_dir / folder_name
                counter += 1
            
            # プロジェクトフォルダのみを作成
            os.makedirs(project_folder, exist_ok=True)
            
            logging.info(f"プロジェクトフォルダを作成しました: {project_folder}")
            return project_folder
                
        except Exception as e:
            logging.error(f"フォルダ作成エラー: {e}")
            raise

    def update_project(self, project_id: int, project_data: Dict[str, Any]) -> None:
        """
        プロジェクト情報の更新
        
        Args:
            project_id: プロジェクトID
            project_data: 更新するプロジェクトデータ
        """
        conn = None
        try:
            # 1. 現在のプロジェクト情報を取得
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM projects WHERE project_id = ?', (project_id,))
            old_project = cursor.fetchone()
            if not old_project:
                raise ValueError(f"プロジェクトが見つかりません: {project_id}")
            
            conn.close()
            conn = None
            
            # 2. プロジェクト情報の更新
            conn = self._get_connection()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE projects 
                SET project_name = ?, start_date = ?, manager = ?,
                    reviewer = ?, approver = ?, division = ?,
                    factory = ?, process = ?, line = ?, status = ?, 
                    updated_at = ?
                WHERE project_id = ?
            ''', (
                project_data['project_name'],
                project_data['start_date'],
                project_data['manager'],
                project_data['reviewer'],
                project_data['approver'],
                project_data['division'],
                project_data['factory'],
                project_data['process'],
                project_data['line'],
                project_data['status'],
                current_time,
                project_id
            ))
            
            conn.commit()
            conn.close()
            conn = None
            
            # 3. 古いフォルダの削除（存在する場合）
            if old_project['project_path']:
                old_path = Path(old_project['project_path'])
                if old_path.exists():
                    shutil.rmtree(old_path)
                    logging.info(f"古いプロジェクトフォルダを削除しました: {old_path}")
            
            # 4. 新しいフォルダの作成
            project_folder = self._create_project_folder(project_data)
            
            # 5. プロジェクトパスの更新
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE projects SET project_path = ? WHERE project_id = ?',
                (str(project_folder), project_id)
            )
            conn.commit()
            conn.close()
            conn = None
            
            # 6. ダッシュボードの更新
            self.update_dashboard()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"プロジェクト更新エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def delete_project(self, project_id: int) -> None:
        """
        プロジェクトの削除
        
        Args:
            project_id: 削除するプロジェクトのID
        """
        conn = None
        try:
            # 1. プロジェクト情報の取得
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM projects WHERE project_id = ?', (project_id,))
            project = cursor.fetchone()
            if not project:
                raise ValueError(f"プロジェクトが見つかりません: {project_id}")
            
            conn.close()
            conn = None
            
            # 2. プロジェクトフォルダの削除
            project_path = project['project_path']
            if project_path and Path(project_path).exists():
                shutil.rmtree(project_path)
                logging.info(f"プロジェクトフォルダを削除しました: {project_path}")
            
            # 3. プロジェクト情報の削除
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM projects WHERE project_id = ?', (project_id,))
            conn.commit()
            conn.close()
            conn = None
            
            # 4. ダッシュボードの更新
            self.update_dashboard()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"プロジェクト削除エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        プロジェクト情報の取得
        
        Args:
            project_id: プロジェクトID
            
        Returns:
            Optional[Dict[str, Any]]: プロジェクト情報
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM projects WHERE project_id = ?', (project_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logging.error(f"プロジェクト取得エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        全プロジェクトの取得
        
        Returns:
            List[Dict[str, Any]]: プロジェクト情報のリスト
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM projects ORDER BY project_id DESC')
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"プロジェクト一覧取得エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def clear_tasks(self):
        """タスクテーブルのデータを全て削除"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks')
            conn.commit()
            logging.info("タスクテーブルのデータを全て削除しました")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"タスクデータ削除エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def insert_tasks(self, tasks_data: List[Dict[str, Any]]) -> None:
        """
        タスクデータの一括登録
        
        Args:
            tasks_data: タスクデータのリスト
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # プロジェクト名の存在確認
            for task in tasks_data:
                cursor.execute(
                    'SELECT COUNT(*) FROM projects WHERE project_name = ?',
                    (task['project_name'],)
                )
                if cursor.fetchone()[0] == 0:
                    raise ValueError(f"プロジェクト '{task['project_name']}' が存在しません")
            
            # タスクデータの挿入
            cursor.executemany('''
                INSERT INTO tasks (
                    task_name, task_start_date, task_finish_date,
                    task_status, task_milestone, task_assignee, task_work_hours, project_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                (
                    task['task_name'],
                    task['task_start_date'],
                    task['task_finish_date'],
                    task['task_status'],
                    task['task_milestone'],
                    task.get('task_assignee', ''),
                    task.get('task_work_hours', 0),
                    task['project_name']
                )
                for task in tasks_data
            ])
            
            conn.commit()
            logging.info(f"{len(tasks_data)}件のタスクを登録しました")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"タスク登録エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def update_dashboard(self):
        """ダッシュボードテーブルを更新し、関連データをエクスポート"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 1. 既存のデータを削除
            cursor.execute('DELETE FROM dashboard')
            
            # 2. プロジェクトとタスクのデータを結合して挿入
            cursor.execute('''
                INSERT INTO dashboard (
                    project_id, project_name, manager, division, factory,
                    process, line, status, created_at, task_id, task_name,
                    task_start_date, task_finish_date, task_status, task_milestone,
                    task_assignee, task_work_hours
                )
                SELECT 
                    p.project_id, p.project_name, p.manager, p.division, 
                    p.factory, p.process, p.line, p.status, p.created_at,
                    t.task_id, t.task_name, t.task_start_date, 
                    t.task_finish_date, t.task_status, t.task_milestone,
                    t.task_assignee, t.task_work_hours
                FROM projects p
                LEFT JOIN tasks t ON p.project_name = t.project_name
            ''')
            
            conn.commit()
            conn.close()
            conn = None
            
            # 3. CSVファイルへの出力
            self._export_dashboard_to_csv()
            self._export_projects_to_csv()
            
            logging.info("ダッシュボードとプロジェクトデータの更新が完了しました")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"ダッシュボード更新エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def _export_dashboard_to_csv(self):
        """ダッシュボードデータをCSVファイルに出力"""
        conn = None
        try:
            # 出力ディレクトリの作成
            os.makedirs(Config.DASHBOARD_EXPORT_DIR, exist_ok=True)
            
            # データの取得
            conn = self._get_connection()
            query = "SELECT * FROM dashboard ORDER BY project_id, task_id"
            df = pd.read_sql_query(query, conn)
            
            # NULL値を "未設定" に変換
            df = df.fillna("未設定")
            
            # CSVファイルに出力
            df.to_csv(
                Config.DASHBOARD_EXPORT_FILE,
                index=False,
                encoding='utf-8-sig'
            )
            
            logging.info(f"ダッシュボードデータをCSVファイルに出力しました: {Config.DASHBOARD_EXPORT_FILE}")
            
        except Exception as e:
            logging.error(f"ダッシュボードデータのCSV出力エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()

    def _export_projects_to_csv(self):
        """プロジェクトデータをCSVファイルに出力"""
        conn = None
        try:
            # 出力ディレクトリの作成
            os.makedirs(Config.DASHBOARD_EXPORT_DIR, exist_ok=True)
            
            # データの取得
            conn = self._get_connection()
            query = """
                SELECT 
                    project_id,
                    project_name,
                    start_date,
                    manager,
                    reviewer,
                    approver,
                    division,
                    factory,
                    process,
                    line,
                    status,
                    project_path,
                    ganttchart_path,
                    created_at,
                    updated_at
                FROM projects
                ORDER BY project_id
            """
            df = pd.read_sql_query(query, conn)
            
            # NULL値を "未設定" に変換
            df = df.fillna("未設定")
            
            # CSVファイルに出力
            df.to_csv(
                Config.PROJECTS_EXPORT_FILE,
                index=False,
                encoding='utf-8-sig'
            )
            
            logging.info(f"プロジェクトデータをCSVファイルに出力しました: {Config.PROJECTS_EXPORT_FILE}")
            
        except Exception as e:
            logging.error(f"プロジェクトデータのCSV出力エラー: {e}")
            raise
        
        finally:
            if conn:
                conn.close()