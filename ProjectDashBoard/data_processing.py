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
        # ダッシュボードデータの読み込み
        logger.info(f"Loading dashboard data from: {dashboard_file_path}")
        df = pd.read_csv(dashboard_file_path)
        
        # プロジェクトデータの読み込み
        projects_file_path = dashboard_file_path.replace('dashboard.csv', 'projects.csv')
        logger.info(f"Loading projects data from: {projects_file_path}")
        
        if not os.path.exists(projects_file_path):
            logger.error(f"Projects data file not found: {projects_file_path}")
            return df
            
        projects_df = pd.read_csv(projects_file_path)
        
        # ganttchart_pathの存在確認
        if 'ganttchart_path' not in projects_df.columns:
            logger.error("ganttchart_path column not found in projects data")
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
                logger.warning(f"Column {col} not found in CSV")
        
        logger.info(f"Data loaded successfully. Total rows: {len(df)}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


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
        
        project_progress['progress'] = (project_progress['completed_tasks'] / 
                                      project_progress['total_tasks'] * 100).round(2)
        project_progress['duration'] = (project_progress['end_date'] - 
                                      project_progress['start_date']).dt.days
        
        return project_progress
    except Exception as e:
        logger.error(f"Error calculating progress: {str(e)}")
        return pd.DataFrame()


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
        logger.error(f"Error getting recent tasks for project {project_id}: {str(e)}")
        return html.Div(
            "データ取得エラー", 
            style={'color': COLORS['status']['danger'], 'fontStyle': 'italic'}
        )