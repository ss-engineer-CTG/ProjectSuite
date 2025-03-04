"""
ダッシュボードのコールバック処理

- ダッシュボード更新処理
- ファイル操作コールバック
"""

import datetime
import logging
import plotly.graph_objects as go
from dash import html, Output, Input, State, ALL, callback_context
from dash.exceptions import PreventUpdate

from ProjectDashBoard.config import COLORS, STYLES
from ProjectDashBoard.data_processing import (
    load_and_process_data, calculate_progress, 
    get_delayed_projects_count
)
from ProjectDashBoard.ui_components import (
    create_project_table, create_progress_distribution, create_duration_distribution
)
from ProjectDashBoard.file_utils import open_file_or_folder

logger = logging.getLogger(__name__)

# ダッシュボード更新用のデータファイルパス
DASHBOARD_FILE_PATH = r'C:\Users\gbrai\Documents\Projects\app_Task_Management\ProjectManager\data\exports\dashboard.csv'


def register_callbacks(app):
    """
    アプリケーションにコールバックを登録する
    
    Args:
        app: Dashアプリケーションオブジェクト
    """
    
    @app.callback(
        [Output('total-projects', 'children'),
        Output('active-projects', 'children'),
        Output('delayed-projects', 'children'),
        Output('milestone-projects', 'children'),
        Output('project-table', 'children'),
        Output('progress-distribution', 'figure'),
        Output('duration-distribution', 'figure'),
        Output('update-time', 'children')],
        [Input('update-button', 'n_clicks')]
    )
    def update_dashboard(n_clicks):
        """
        ダッシュボードの更新処理
        
        Args:
            n_clicks: 更新ボタンのクリック回数
            
        Returns:
            更新された値のタプル
        """
        try:
            # データの読み込みと処理
            df = load_and_process_data(DASHBOARD_FILE_PATH)
            progress_data = calculate_progress(df)
            
            # 統計の計算
            total_projects = len(progress_data)
            active_projects = len(progress_data[progress_data['progress'] < 100])
            delayed_projects = get_delayed_projects_count(df)
            milestone_projects = len(df[
                (df['task_milestone'] == '○') & 
                (df['task_finish_date'].dt.month == datetime.datetime.now().month)
            ]['project_id'].unique())
            
            # テーブルとグラフの生成
            table = create_project_table(df, progress_data)
            progress_fig = create_progress_distribution(progress_data)
            duration_fig = create_duration_distribution(progress_data)
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return (
                str(total_projects),
                str(active_projects),
                str(delayed_projects),
                str(milestone_projects),
                table,
                progress_fig,
                duration_fig,
                f'最終更新: {current_time}'
            )
        
        except Exception as e:
            logger.error(f"Error updating dashboard: {str(e)}")
            # エラー時のフォールバック値を返す
            return (
                '0', '0', '0', '0',
                html.Div('データの読み込みに失敗しました', style={'color': COLORS['status']['danger']}),
                go.Figure(),
                go.Figure(),
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

    @app.callback(
        [Output('dummy-output', 'children'),
        Output('notification-container', 'children')],
        [Input({'type': 'open-path-button', 'path': ALL, 'action': ALL}, 'n_clicks')],
        [State({'type': 'open-path-button', 'path': ALL, 'action': ALL}, 'id')]
    )
    def handle_button_click(n_clicks_list, button_ids):
        """
        ボタンクリックイベントの処理
        
        Args:
            n_clicks_list: クリック回数のリスト
            button_ids: ボタンIDのリスト
            
        Returns:
            通知メッセージとダミー出力
        """
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            raise PreventUpdate
        
        try:
            # クリックされたボタンのインデックスを特定
            button_index = next(
                i for i, n_clicks in enumerate(n_clicks_list)
                if n_clicks is not None and n_clicks > 0
            )
            path = button_ids[button_index]['path']
            action = button_ids[button_index]['action']
            
            if not path:
                return '', html.Div(
                    'Invalid path specified',
                    style={**STYLES['notification']['error'], 'opacity': 1}
                )
            
            # アクションタイプに基づいて許可するパスタイプを決定
            allow_directories = (action == 'フォルダを開く')
            
            # ファイル/フォルダを開く
            result = open_file_or_folder(path, allow_directories)
            
            # 結果に基づいて通知を表示
            notification_style = (
                STYLES['notification']['success']
                if result['success']
                else STYLES['notification']['error']
            )
            
            return '', html.Div(
                result['message'],
                style={**notification_style, 'opacity': 1}
            )
            
        except Exception as e:
            logger.error(f"Error in callback: {str(e)}")
            return '', html.Div(
                'An error occurred',
                style={**STYLES['notification']['error'], 'opacity': 1}
            )