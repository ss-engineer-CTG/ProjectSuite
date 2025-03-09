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
import shutil
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
            
            # ★★★ 修正: Config クラスを直接インポートして参照 ★★★
            from ProjectManager.src.core.config import Config
            
            # 環境変数にデータパスを設定
            export_dir = str(Config.DASHBOARD_EXPORT_DIR)
            dashboard_file = str(Config.DASHBOARD_EXPORT_FILE)
            os.environ['PMSUITE_DASHBOARD_DATA_DIR'] = export_dir
            os.environ['PMSUITE_DASHBOARD_FILE'] = dashboard_file
            self.logger.info(f"Dashboard data directory set: {export_dir}")
            self.logger.info(f"Dashboard file path set: {dashboard_file}")
            
            # 既に起動している場合は何もしない
            if self.dashboard_process and self.dashboard_process.poll() is None:
                # ブラウザだけ開く
                webbrowser.open('http://127.0.0.1:8050')
                self.logger.info("既存のダッシュボードプロセスを再利用します")
                return
            
            # PyInstaller環境と通常環境で起動方法を分ける
            if getattr(sys, 'frozen', False):
                # パッケージ環境ではバッチファイルを使用
                self.logger.info("パッケージ環境でダッシュボードを起動")
                
                # バッチファイルが実行可能な場所にあるか確認
                batch_path = Path(sys._MEIPASS).parent / "dashboard_launcher.bat"
                
                if not batch_path.exists():
                    # バッチファイルが存在しない場合は作成
                    self.logger.info(f"バッチファイルを作成: {batch_path}")
                    with open(batch_path, 'w') as f:
                        f.write('@echo off\n')
                        f.write('REM ダッシュボード起動スクリプト\n')
                        f.write('SET PYTHONPATH=%~dp0\n')
                        f.write('"%~dp0ProjectManagerSuite.exe" ProjectDashBoard\n')
                
                # バッチファイルを実行
                self.logger.info(f"バッチファイル実行: {batch_path}")
                self.dashboard_process = subprocess.Popen(
                    [str(batch_path)],
                    shell=True,
                    cwd=str(batch_path.parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                # 開発環境では直接モジュールを実行
                python_executable = sys.executable
                self.logger.info("開発環境でダッシュボードを起動")
                
                # mainモジュールのスタンドアロン実行機能を使用
                cmd = [
                    python_executable,
                    "-m", 
                    "ProjectManager.src.main",
                    "ProjectDashBoard"
                ]
                
                self.dashboard_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            # 非同期でログを取得
            threading.Thread(
                target=self._log_subprocess_output,
                args=(self.dashboard_process,),
                daemon=True
            ).start()
            
            # 別スレッドでブラウザを開く
            threading.Thread(target=self._open_browser_when_ready).start()
            
            self.logger.info("ダッシュボード起動プロセスを開始しました")
            
        except Exception as e:
            self.logger.error(f"ダッシュボード起動エラー: {e}")
            raise
    
    def _log_subprocess_output(self, process):
        """サブプロセスの出力をログに記録する"""
        while True:
            if process.poll() is not None:  # プロセスが終了した場合
                # 残りの出力を読み取る
                stdout, stderr = process.communicate()
                if stdout:
                    self.logger.info(f"ダッシュボード出力: {stdout}")
                if stderr:
                    self.logger.error(f"ダッシュボードエラー: {stderr}")
                break
            
            # 標準出力の読み取り
            output = process.stdout.readline()
            if output:
                self.logger.info(f"ダッシュボード出力: {output.strip()}")
            
            # 標準エラー出力の読み取り
            error = process.stderr.readline()
            if error:
                self.logger.error(f"ダッシュボードエラー: {error.strip()}")
                
            # 短い待機
            time.sleep(0.1)
    
    def _get_dashboard_path(self) -> Path:
        """
        ダッシュボードのpathを取得する
        
        Returns:
            Path: ダッシュボードアプリケーションのパス
        """
        # 実行環境に応じたパス解決
        if getattr(sys, 'frozen', False):
            # PyInstallerで実行ファイル化した場合
            dashboard_path = Path(sys._MEIPASS) / "ProjectDashBoard" / "app.py"
        else:
            # 通常実行時は現在のモジュールからの相対パスを使用
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
        max_retries = 30  # 試行回数を増加
        retry_delay = 1.0  # 待機時間を増加
        
        for attempt in range(max_retries):
            try:
                # サーバーが起動しているか確認
                response = requests.get('http://127.0.0.1:8050', timeout=1.0)
                if response.status_code == 200:
                    # サーバーが応答するようになったらブラウザを開く
                    self.logger.info(f"サーバーが応答しました（試行回数: {attempt + 1}）")
                    webbrowser.open('http://127.0.0.1:8050')
                    self.logger.info("ブラウザでダッシュボードを開きました")
                    return
            except RequestException:
                # まだ準備ができていない、待機を続ける
                pass
                
            # プロセスが終了していないか確認
            if self.dashboard_process and self.dashboard_process.poll() is not None:
                self.logger.error("サーバープロセスが予期せず終了しました")
                return
                
            # 次の試行まで待機
            time.sleep(retry_delay)
            
        # 最大試行回数に達した場合でもブラウザは開く
        self.logger.warning(f"サーバー応答を待機したが、{max_retries}回の試行でタイムアウトしました")
        webbrowser.open('http://127.0.0.1:8050')
    
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
                    self.logger.info("ダッシュボードプロセスが強制終了しました")
                    self.dashboard_process = None
            
            except Exception as e:
                self.logger.error(f"ダッシュボード終了エラー: {e}")