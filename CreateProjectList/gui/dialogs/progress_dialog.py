# gui/dialogs/progress_dialog.py

import tkinter as tk
from tkinter import ttk
import threading
from typing import Optional, Callable
import queue
from .base_dialog import BaseDialog

class ProgressDialog(BaseDialog):
    """進捗表示ダイアログ"""
    
    def __init__(self, parent: tk.Tk, title: str):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            title: ダイアログのタイトル
        """
        super().__init__(parent, title, modal=True)
        
        # サイズ変更を禁止
        self.dialog.resizable(False, False)
        
        # UI要素
        self.setup_ui()
        
        # 処理用の変数
        self.is_cancelled = False
        self.worker_thread: Optional[threading.Thread] = None
        self.queue = queue.Queue()
    
    def setup_ui(self):
        """UI要素の構築"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # プログレスバー
        self.progress = ttk.Progressbar(
            main_frame,
            length=300,
            mode='determinate'
        )
        self.progress.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        # ステータスメッセージ
        self.status_var = tk.StringVar(value="処理を開始します...")
        self.status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            wraplength=280,
            style='Dialog.TLabel'
        )
        self.status_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # 詳細メッセージ
        self.detail_var = tk.StringVar()
        self.detail_label = ttk.Label(
            main_frame,
            textvariable=self.detail_var,
            wraplength=280,
            foreground='gray',
            style='Dialog.TLabel'
        )
        self.detail_label.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        # キャンセルボタン
        self.cancel_button = ttk.Button(
            main_frame,
            text="キャンセル",
            command=self.cancel,
            style='Dialog.TButton'
        )
        self.cancel_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # グリッド設定
        self.dialog.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
    
    def start_process(self, process_func: Callable, *args, **kwargs):
        """
        処理を開始
        
        Args:
            process_func: 実行する処理関数
            *args: 処理関数に渡す位置引数
            **kwargs: 処理関数に渡すキーワード引数
        """
        self.is_cancelled = False
        
        # ワーカースレッドの作成
        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(process_func, args, kwargs)
        )
        self.worker_thread.daemon = True  # メインスレッド終了時に強制終了
        self.worker_thread.start()
        
        # 進捗更新の開始
        self.dialog.after(100, self.update_progress)
    
    def _worker(self, process_func: Callable, args, kwargs):
        """
        ワーカースレッドの処理
        
        Args:
            process_func: 実行する処理関数
            args: 処理関数に渡す位置引数
            kwargs: 処理関数に渡すキーワード引数
        """
        try:
            # プログレスコールバックを追加
            kwargs['progress_callback'] = self.update_status
            kwargs['cancel_check'] = lambda: self.is_cancelled
            
            # 処理の実行
            result = process_func(*args, **kwargs)
            
            # 結果の送信
            if result.get('cancelled', False):
                self.queue.put(("cancelled", None))
            elif result.get('errors'):
                self.queue.put(("error", result['errors']))
            else:
                self.queue.put(("finished", result))
                
        except Exception as e:
            self.logger.error(f"Process error: {str(e)}")
            self.queue.put(("error", str(e)))
    
    def update_progress(self):
        """進捗表示の更新"""
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                self.logger.debug(f"Progress update: {msg_type}, {data}")
                
                if msg_type == "progress":
                    value, status, detail = data
                    self.progress["value"] = value
                    self.status_var.set(status)
                    if detail:
                        self.detail_var.set(detail)
                
                elif msg_type == "error":
                    if isinstance(data, list):
                        # エラーリストの表示
                        error_message = "処理中に以下のエラーが発生しました:\n\n"
                        for file_path, error in data:
                            # フォルダ重複エラーの場合は特別な表示
                            if "出力先に既存のディレクトリが存在します" in str(error):
                                error_message += f"- 既存フォルダが存在します: {file_path}\n"
                            else:
                                error_message += f"- {file_path.name}: {error}\n"
                    else:
                        error_message = f"処理中にエラーが発生しました:\n{data}"
                    
                    self.show_error(error_message)
                    self._on_closing()
                    return
                
                elif msg_type == "cancelled":
                    self.show_info("処理がキャンセルされました。")
                    self._on_closing()
                    return
                
                elif msg_type == "finished":
                    self.show_info("処理が完了しました。")
                    self._trigger_event("finished", result=data)
                    self._on_closing()
                    return
                
        except queue.Empty:
            pass
        
        if not self.is_cancelled:
            self.dialog.after(100, self.update_progress)
    
    def update_status(self, progress: float, status: str, detail: str = ""):
        """
        状態の更新
        
        Args:
            progress: 進捗率（0-100）
            status: 状態メッセージ
            detail: 詳細メッセージ
        """
        self.queue.put(("progress", (progress, status, detail)))
    
    def cancel(self):
        """処理のキャンセル"""
        if not self.is_cancelled:
            self.is_cancelled = True
            self.cancel_button.configure(state='disabled')
            self.status_var.set("処理をキャンセルしています...")
            self.detail_var.set("しばらくお待ちください...")
    
    def _on_closing(self):
        """ダイアログが閉じられるときの処理"""
        self.cancel()  # 実行中の処理をキャンセル
        super()._on_closing()