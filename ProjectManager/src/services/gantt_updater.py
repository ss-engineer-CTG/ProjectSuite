import logging
from pathlib import Path
from typing import Optional, List, Dict
import sqlite3
import traceback

class GanttChartUpdater:
    """ガントチャートパス更新クラス"""
    
    def __init__(self, db_manager):
        """
        初期化
        
        Args:
            db_manager: データベースマネージャーインスタンス
        """
        self.db_manager = db_manager
        
    def update_ganttchart_paths(self) -> Dict[str, int]:
        """
        全プロジェクトのガントチャートパスを更新
        
        Returns:
            Dict[str, int]: 処理結果の統計情報
        """
        stats = {
            'total': 0,        # 処理対象の総プロジェクト数
            'updated': 0,      # パス更新に成功したプロジェクト数
            'not_found': 0,    # ガントチャートが見つからなかったプロジェクト数
            'error': 0         # エラーが発生したプロジェクト数
        }
        
        try:
            # プロジェクトテーブルにganttchart_path列が存在することを確認
            self._ensure_ganttchart_column()
            
            # 全プロジェクトのパスを取得
            all_projects = self.db_manager.get_all_projects()
            stats['total'] = len(all_projects)
            
            for project in all_projects:
                try:
                    project_path = project.get('project_path')
                    if not project_path or not Path(project_path).exists():
                        logging.warning(f"プロジェクトパスが無効です: {project['project_name']}")
                        stats['not_found'] += 1
                        continue
                    
                    # ガントチャートファイルを検索
                    gantt_path = self._find_ganttchart(Path(project_path))
                    
                    if gantt_path:
                        # パスをデータベースに保存
                        self._update_ganttchart_path(
                            project['project_id'],
                            str(gantt_path)
                        )
                        stats['updated'] += 1
                        logging.info(
                            f"ガントチャートパスを更新しました: {project['project_name']}"
                        )
                    else:
                        stats['not_found'] += 1
                        logging.warning(
                            f"ガントチャートが見つかりません: {project['project_name']}"
                        )
                
                except Exception as e:
                    stats['error'] += 1
                    logging.error(
                        f"プロジェクト '{project['project_name']}' の処理中にエラー: {e}\n"
                        f"{traceback.format_exc()}"
                    )
            
            return stats
            
        except Exception as e:
            logging.error(f"ガントチャートパス更新処理でエラー: {e}\n{traceback.format_exc()}")
            raise
            
    def _ensure_ganttchart_column(self):
        """ganttchart_path列の存在を確認し、必要に応じて追加"""
        conn = None
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # 列の存在確認
            cursor.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # 列が存在しない場合は追加
            if 'ganttchart_path' not in columns:
                cursor.execute(
                    'ALTER TABLE projects ADD COLUMN ganttchart_path TEXT'
                )
                conn.commit()
                logging.info("ganttchart_path列を追加しました")
                
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"テーブル構造の更新でエラー: {e}")
            raise
            
        finally:
            if conn:
                conn.close()
                
    def _find_ganttchart(self, project_path: Path) -> Optional[Path]:
        """
        プロジェクトフォルダ内のガントチャートファイルを検索
        
        Args:
            project_path: プロジェクトフォルダのパス
            
        Returns:
            Optional[Path]: ガントチャートファイルのパス。見つからない場合はNone
        """
        try:
            # 「工程表」を含むフォルダを検索
            process_folders = []
            for folder in project_path.rglob('*'):
                if folder.is_dir() and '工程表' in folder.name:
                    process_folders.append(folder)
            
            # 各フォルダ内でガントチャートファイルを検索
            for folder in process_folders:
                for file in folder.glob('*.xlsm'):
                    if '工程表作成補助アプリ' in file.name:
                        return file
                        
            return None
            
        except Exception as e:
            logging.error(f"ガントチャートファイルの検索でエラー: {e}")
            return None
            
    def _update_ganttchart_path(self, project_id: int, gantt_path: str):
        """
        プロジェクトのガントチャートパスを更新
        
        Args:
            project_id: プロジェクトID
            gantt_path: ガントチャートファイルのパス
        """
        conn = None
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE projects SET ganttchart_path = ? WHERE project_id = ?',
                (gantt_path, project_id)
            )
            
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"ガントチャートパスの更新でエラー: {e}")
            raise
            
        finally:
            if conn:
                conn.close()