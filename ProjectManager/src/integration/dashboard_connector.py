"""ダッシュボードとの連携を管理する統合モジュール"""

import subprocess
import webbrowser
import threading
import time
from pathlib import Path
import logging
import sys
import os
import requests
from requests.exceptions import RequestException

class DashboardConnector:
    """ダッシュボードとの連携を管理するクラス"""
    
    def __init__(self, db_manager):
        """
        初期化
        
        Args:
            db_manager: データベースマネージャーインスタンス
        """
        self.db_manager = db_manager
        self.dashboard_process = None
        self.logger = logging.getLogger(__name__)
        
    def launch_dashboard(self):
        """
        ダッシュボードアプリケーションを起動し、ブラウザで表示する
        
        Raises:
            Exception: 起動に失敗した場合
        """
        try:
            # CSVデータを最新に更新
            self.db_manager.update_dashboard()
            
            # 既に起動している場合は何もしない
            if self.dashboard_process and self.dashboard_process.poll() is None:
                # ブラウザだけ開く
                webbrowser.open('http://127.0.0.1:8050')
                self.logger.info("既存のダッシュボードプロセスを再利用します")
                return
                
            # ダッシュボードを別プロセスで起動
            dashboard_path = self._get_dashboard_path()
            
            # 環境変数を設定してデバッグモードを無効化
            env = os.environ.copy()
            
            # Pythonパスを取得して使用
            python_executable = sys.executable
            
            # ダッシュボードを起動
            self.logger.info(f"ダッシュボードを起動します: {dashboard_path}")
            self.dashboard_process = subprocess.Popen(
                [python_executable, str(dashboard_path)],
                env=env
            )
            
            # 別スレッドでブラウザを開く
            threading.Thread(target=self._open_browser_when_ready).start()
            
            self.logger.info("ダッシュボードを起動しました")
            
        except Exception as e:
            self.logger.error(f"ダッシュボード起動エラー: {e}")
            raise
    
    def _get_dashboard_path(self) -> Path:
        """
        ダッシュボードのpathを取得する
        
        Returns:
            Path: ダッシュボードアプリケーションのパス
        """
        # 現在のモジュールからの相対パスを使用
        current_dir = Path(__file__).parent.parent.parent.parent
        dashboard_path = current_dir / "ProjectDashBoard" / "app.py"
        
        # パスの検証
        if not dashboard_path.exists():
            # 見つからない場合は代替パスを試す
            alt_path = Path(__file__).parent.parent.parent.parent.parent / "ProjectDashBoard" / "app.py"
            if alt_path.exists():
                return alt_path
            else:
                raise FileNotFoundError(f"ダッシュボードアプリケーションが見つかりません: {dashboard_path}")
        
        return dashboard_path
    
    def _open_browser_when_ready(self):
        """
        サーバーが起動するまで待ってからブラウザを開く
        """
        try:
            # サーバー起動を待つ
            time.sleep(3)
            webbrowser.open('http://127.0.0.1:8050')
            self.logger.info("ブラウザでダッシュボードを開きました")
        except Exception as e:
            self.logger.error(f"ブラウザ起動エラー: {e}")
    
    def shutdown_dashboard(self):
        """ダッシュボードサーバーを明示的に終了する"""
        try:
            # HTTPリクエストでシャットダウンを要求
            try:
                response = requests.post('http://127.0.0.1:8050/shutdown', timeout=3)
                if response.status_code == 200:
                    self.logger.info("ダッシュボードシャットダウンリクエストを送信しました")
                    # レスポンスを待つ
                    time.sleep(1)
                else:
                    self.logger.warning(f"シャットダウンリクエスト失敗: {response.status_code}")
            except RequestException as e:
                self.logger.debug(f"シャットダウンリクエスト中にエラー: {e}")
        
            # プロセスの終了も試みる（バックアップ）
            self.shutdown()
        except Exception as e:
            self.logger.error(f"ダッシュボード終了中にエラー: {e}")
        
    def refresh_dashboard(self):
        """
        データを更新してダッシュボードを更新する
        
        Raises:
            Exception: 更新に失敗した場合
        """
        try:
            self.db_manager.update_dashboard()
            self.logger.info("ダッシュボードデータを更新しました")
        except Exception as e:
            self.logger.error(f"ダッシュボードデータ更新エラー: {e}")
            raise
    
    def shutdown(self):
        """
        ダッシュボードプロセスを終了する
        """
        if self.dashboard_process:
            try:
                self.logger.info("ダッシュボードプロセスを終了します")
                
                # まずは正常終了を試みる
                self.dashboard_process.terminate()
                
                # 終了を待機
                try:
                    self.dashboard_process.wait(timeout=5)
                    self.logger.info("ダッシュボードプロセスが正常終了しました")
                except subprocess.TimeoutExpired:
                    # 強制終了
                    self.logger.warning("ダッシュボードプロセスを強制終了します")
                    self.dashboard_process.kill()
                    self.dashboard_process.wait(timeout=2)
                    self.logger.info("ダッシュボードプロセスを強制終了しました")
                
                self.dashboard_process = None
                
            except Exception as e:
                self.logger.error(f"ダッシュボード終了エラー: {e}")