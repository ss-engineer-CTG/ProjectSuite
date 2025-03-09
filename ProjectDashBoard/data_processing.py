"""
プロジェクト管理データの処理モジュール

- データの読み込みと処理
- 進捗計算
- 遅延検出
- マイルストーン関連処理
"""

import os
import pandas as pd
import datetime
import logging
from typing import Optional, Tuple
import sys
import traceback
from pathlib import Path
from dash import html

from ProjectDashBoard.config import COLORS

logger = logging.getLogger(__name__)


def load_and_process_data(dashboard_file_path: str) -> pd.DataFrame:
    """
    データの読み込みと処理
    
    Args:
        dashboard_file_path: ダッシュボードCSVファイルパス
        
    Returns:
        処理済みのデータフレーム
    """
    try:
        # ★★★ 追加: 詳細なパス検証とエラーハンドリング ★★★
        logger.info(f"ダッシュボードデータの読み込み開始: {dashboard_file_path}")
        
        # パスの存在確認
        if not os.path.exists(dashboard_file_path):
            logger.error(f"ダッシュボードファイルが見つかりません: {dashboard_file_path}")
            
            # 診断情報の記録
            logger.error(f"現在の作業ディレクトリ: {os.getcwd()}")
            logger.error(f"環境変数: PMSUITE_DASHBOARD_DATA_DIR={os.environ.get('PMSUITE_DASHBOARD_DATA_DIR', '未設定')}")
            logger.error(f"環境変数: PMSUITE_DASHBOARD_FILE={os.environ.get('PMSUITE_DASHBOARD_FILE', '未設定')}")
            
            # PyInstaller環境の場合、追加情報を出力
            if getattr(sys, 'frozen', False):
                logger.error(f"PyInstaller MEIPASS: {sys._MEIPASS}")
                logger.error(f"実行ファイルパス: {sys.executable}")
            
            # 検索した他のパスの情報も記録
            for path_to_check in [
                Path.cwd() / "data" / "exports" / "dashboard.csv",
                Path.home() / "ProjectManagerSuite" / "data" / "exports" / "dashboard.csv"
            ]:
                logger.error(f"代替パスの存在確認: {path_to_check} - {'存在します' if path_to_check.exists() else '存在しません'}")
            
            # エラーメッセージ付きのデータフレームを返す
            error_df = pd.DataFrame({
                "error_message": [f"データファイルが見つかりません: {dashboard_file_path}"],
                "additional_info": ["データの更新または再インストールをお試しください。"]
            })
            return error_df
            
        # ダッシュボードデータの読み込み
        logger.info(f"ファイルの読み込み: {dashboard_file_path}")
        
        # CSV読み込みでエンコーディングを複数試す
        df = None
        for encoding in ['utf-8-sig', 'utf-8', 'cp932']:
            try:
                df = pd.read_csv(dashboard_file_path, encoding=encoding)
                logger.info(f"CSVを読み込みました (エンコーディング: {encoding})")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"CSVの読み込みエラー ({encoding}): {e}")
        
        if df is None:
            logger.error("すべてのエンコーディングで読み込みに失敗しました")
            return pd.DataFrame({"error": ["CSVファイルの読み込みに失敗しました。ファイルが破損している可能性があります。"]})
        
        # プロジェクトデータの読み込み
        projects_file_path = dashboard_file_path.replace('dashboard.csv', 'projects.csv')
        logger.info(f"プロジェクトデータを読み込み: {projects_file_path}")
        
        if not os.path.exists(projects_file_path):
            logger.error(f"プロジェクトデータファイルが見つかりません: {projects_file_path}")
            return df
            
        projects_df = pd.read_csv(projects_file_path)
        
        # ganttchart_pathの存在確認
        if 'ganttchart_path' not in projects_df.columns:
            logger.error("ganttchart_path列がプロジェクトデータにありません")
            return df

        # パスの検証
        from ProjectDashBoard.file_utils import validate_file_path
        projects_df['ganttchart_path'] = projects_df['ganttchart_path'].apply(
            lambda x: None if pd.isna(x) else validate_file_path(x)
        )
        
        # データの結合
        df = pd.merge(
            df,
            projects_df[['project_id', 'project_path', 'ganttchart_path']],
            on='project_id',
            how='left'
        )
        
        # 日付列の処理
        date_columns = ['task_start_date', 'task_finish_date', 'created_at']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            else:
                logger.warning(f"列 {col} がCSVにありません")
        
        logger.info(f"データの読み込み完了。合計行数: {len(df)}")
        return df
        
    except Exception as e:
        logger.error(f"データ読み込みエラー: {str(e)}")
        logger.error(traceback.format_exc())
        # エラーメッセージを含む空のデータフレームを返す
        return pd.DataFrame({"error": [f"データ読み込みエラー: {str(e)}"]})


def check_delays(df: pd.DataFrame) -> pd.DataFrame:
    """
    遅延タスクの検出
    
    Args:
        df: データフレーム
        
    Returns:
        遅延タスクのデータフレーム
    """
    current_date = datetime.datetime.now()
    return df[
        (df['task_finish_date'] < current_date) & 
        (df['task_status'] != '完了')
    ]


def get_delayed_projects_count(df: pd.DataFrame) -> int:
    """
    遅延プロジェクト数を計算
    遅延タスクを持つプロジェクトの数を返す
    
    Args:
        df: データフレーム
        
    Returns:
        遅延プロジェクト数
    """
    delayed_tasks = check_delays(df)
    return len(delayed_tasks['project_id'].unique())


def calculate_progress(df: pd.DataFrame) -> pd.DataFrame:
    """
    プロジェクト進捗の計算
    
    Args:
        df: データフレーム
        
    Returns:
        プロジェクト進捗のデータフレーム
    """
    try:
        # ★★★ 追加: 空のデータフレームまたはエラーメッセージを含むデータフレームのチェック ★★★
        if df.empty:
            logger.warning("空のデータフレームでの進捗計算が試行されました")
            return pd.DataFrame(columns=[
                'project_id', 'project_name', 'process', 'line',
                'total_tasks', 'completed_tasks', 'milestone_count',
                'start_date', 'end_date', 'project_path', 'ganttchart_path',
                'progress', 'duration'
            ])
        
        if 'error' in df.columns:
            logger.warning("エラーメッセージを含むデータフレームでの進捗計算が試行されました")
            # エラーデータフレームから最小限の進捗データフレームを生成
            return pd.DataFrame({
                'project_id': [0],
                'project_name': ['エラー'],
                'process': ['N/A'],
                'line': ['N/A'],
                'total_tasks': [0],
                'completed_tasks': [0],
                'milestone_count': [0],
                'start_date': [datetime.datetime.now()],
                'end_date': [datetime.datetime.now()],
                'project_path': [''],
                'ganttchart_path': [''],
                'progress': [0],
                'duration': [0]
            })
        
        # 必要なカラムの存在確認
        required_columns = ['project_id', 'project_name', 'task_id', 'task_status', 
                           'task_start_date', 'task_finish_date']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"進捗計算に必要なカラムがありません: {missing_columns}")
            return pd.DataFrame({
                'project_id': [0],
                'project_name': ['データエラー'],
                'process': ['N/A'],
                'line': ['N/A'],
                'total_tasks': [0],
                'completed_tasks': [0],
                'milestone_count': [0],
                'start_date': [datetime.datetime.now()],
                'end_date': [datetime.datetime.now()],
                'project_path': [''],
                'ganttchart_path': [''],
                'progress': [0],
                'duration': [0]
            })
            
        # 通常の進捗計算
        project_progress = df.groupby('project_id').agg({
            'project_name': 'first',
            'process': 'first',
            'line': 'first',
            'task_id': ['count', lambda x: sum(df.loc[x.index, 'task_status'] == '完了')],
            'task_milestone': lambda x: x.str.contains('○').sum(),
            'task_start_date': 'min',
            'task_finish_date': 'max',
            'project_path': 'first',
            'ganttchart_path': 'first'
        }).reset_index()
        
        project_progress.columns = [
            'project_id', 'project_name', 'process', 'line',
            'total_tasks', 'completed_tasks', 'milestone_count',
            'start_date', 'end_date', 'project_path', 'ganttchart_path'
        ]
        
        # 進捗率と期間の計算
        project_progress['progress'] = (project_progress['completed_tasks'] / 
                                      project_progress['total_tasks'] * 100).round(2)
        project_progress['duration'] = (project_progress['end_date'] - 
                                      project_progress['start_date']).dt.days
        
        return project_progress
    except Exception as e:
        logger.error(f"進捗計算エラー: {str(e)}")
        logger.error(traceback.format_exc())
        # 最小限のデータフレームを返す
        return pd.DataFrame({
            'project_id': [0],
            'project_name': ['計算エラー'],
            'process': ['N/A'],
            'line': ['N/A'],
            'total_tasks': [0],
            'completed_tasks': [0],
            'milestone_count': [0],
            'start_date': [datetime.datetime.now()],
            'end_date': [datetime.datetime.now()],
            'project_path': [''],
            'ganttchart_path': [''],
            'progress': [0],
            'duration': [0]
        })


def get_status_color(progress: float, has_delay: bool) -> str:
    """
    進捗状況に応じた色を返す
    
    Args:
        progress: 進捗率
        has_delay: 遅延フラグ
        
    Returns:
        色コード
    """
    if has_delay:
        return COLORS['status']['danger']
    elif progress >= 90:
        return COLORS['status']['success']
    elif progress >= 70:
        return COLORS['status']['info']
    elif progress >= 50:
        return COLORS['status']['warning']
    return COLORS['status']['neutral']


def get_next_milestone(df: pd.DataFrame) -> pd.DataFrame:
    """
    次のマイルストーンを取得
    
    Args:
        df: データフレーム
        
    Returns:
        次のマイルストーンのデータフレーム
    """
    current_date = datetime.datetime.now()
    return df[
        (df['task_milestone'] == '○') & 
        (df['task_finish_date'] > current_date)
    ].sort_values('task_finish_date')


def next_milestone_format(next_milestones: pd.DataFrame, project_id: str) -> str:
    """
    マイルストーン表示のフォーマット
    
    Args:
        next_milestones: マイルストーンのデータフレーム
        project_id: プロジェクトID
        
    Returns:
        フォーマット済みのマイルストーン文字列
    """
    milestone = next_milestones[next_milestones['project_id'] == project_id]
    if len(milestone) == 0:
        return '-'
    next_date = milestone.iloc[0]['task_finish_date']
    days_until = (next_date - datetime.datetime.now()).days
    return f"{milestone.iloc[0]['task_name']} ({days_until}日後)"


def get_recent_tasks(df: pd.DataFrame, project_id: str) -> html.Div:
    """
    プロジェクトの直近のタスク情報を取得し、表示用のDivを生成する
    
    Args:
        df: データフレーム
        project_id: プロジェクトID
        
    Returns:
        直近のタスク情報を含むDiv要素
    """
    try:
        current_date = datetime.datetime.now()
        project_tasks = df[df['project_id'] == project_id]
        
        # 遅延中タスク
        delayed_tasks = project_tasks[
            (project_tasks['task_finish_date'] < current_date) & 
            (project_tasks['task_status'] != '完了')
        ].sort_values('task_finish_date')
        
        # 進行中タスク（現在の日付が開始日と終了日の間にあるタスク）
        in_progress_tasks = project_tasks[
            (project_tasks['task_status'] != '完了') & 
            (project_tasks['task_start_date'] <= current_date) &
            (project_tasks['task_finish_date'] >= current_date)
        ].sort_values('task_finish_date')
        
        # 次のタスク（現在日より後に開始予定で最も近いもの）
        next_tasks = project_tasks[
            (project_tasks['task_status'] != '完了') & 
            (project_tasks['task_start_date'] > current_date)
        ].sort_values('task_start_date')
        
        # HTMLコンテンツの作成
        content_elements = []
        
        # 遅延中タスク - タスク名にも色を指定
        if len(delayed_tasks) > 0:
            content_elements.append(html.Div([
                html.Span("遅延中: ", style={'fontWeight': 'bold', 'color': COLORS['status']['danger']}),
                html.Span(delayed_tasks.iloc[0]['task_name'], style={
                    'wordBreak': 'break-word',
                    'color': COLORS['text']['primary'] # 白色を明示的に指定
                })
            ]))
        else:
            content_elements.append(html.Div([
                html.Span("遅延中: ", style={'fontWeight': 'bold', 'color': COLORS['status']['danger']}),
                html.Span("なし", style={'fontStyle': 'italic', 'color': COLORS['text']['secondary']})
            ]))
        
        # 進行中タスク - タスク名にも色を指定
        if len(in_progress_tasks) > 0:
            content_elements.append(html.Div([
                html.Span("進行中: ", style={'fontWeight': 'bold', 'color': COLORS['status']['info']}),
                html.Span(in_progress_tasks.iloc[0]['task_name'], style={
                    'wordBreak': 'break-word',
                    'color': COLORS['text']['primary'] # 白色を明示的に指定
                })
            ]))
        else:
            content_elements.append(html.Div([
                html.Span("進行中: ", style={'fontWeight': 'bold', 'color': COLORS['status']['info']}),
                html.Span("なし", style={'fontStyle': 'italic', 'color': COLORS['text']['secondary']})
            ]))
        
        # 次のタスク - タスク名にも色を指定
        if len(next_tasks) > 0:
            content_elements.append(html.Div([
                html.Span("次のタスク: ", style={'fontWeight': 'bold', 'color': COLORS['text']['accent']}),
                html.Span(next_tasks.iloc[0]['task_name'], style={
                    'wordBreak': 'break-word',
                    'color': COLORS['text']['primary'] # 白色を明示的に指定
                })
            ]))
        else:
            content_elements.append(html.Div([
                html.Span("次のタスク: ", style={'fontWeight': 'bold', 'color': COLORS['text']['accent']}),
                html.Span("なし", style={'fontStyle': 'italic', 'color': COLORS['text']['secondary']})
            ]))
        
        # 次の次のタスク - タスク名にも色を指定
        if len(next_tasks) > 1:
            content_elements.append(html.Div([
                html.Span("次の次: ", style={'fontWeight': 'bold', 'color': COLORS['text']['secondary']}),
                html.Span(next_tasks.iloc[1]['task_name'], style={
                    'wordBreak': 'break-word',
                    'color': COLORS['text']['primary'] # 白色を明示的に指定
                })
            ]))
        else:
            content_elements.append(html.Div([
                html.Span("次の次: ", style={'fontWeight': 'bold', 'color': COLORS['text']['secondary']}),
                html.Span("なし", style={'fontStyle': 'italic', 'color': COLORS['text']['secondary']})
            ]))
        
        return html.Div(content_elements, style={'fontSize': '0.9em'})
        
    except Exception as e:
        logger.error(f"プロジェクト {project_id} の直近タスク取得エラー: {str(e)}")
        return html.Div(
            "データ取得エラー", 
            style={'color': COLORS['status']['danger'], 'fontStyle': 'italic'}
        )