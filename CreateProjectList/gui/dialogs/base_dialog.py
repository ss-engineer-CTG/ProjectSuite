# gui/dialogs/base_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Dict, Any, Callable
from CreateProjectList.utils.log_manager import LogManager

class BaseDialog:
    """ダイアログの基底クラス"""
    
    def __init__(self, parent: tk.Tk, title: str, modal: bool = True):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            title: ダイアログのタイトル
            modal: モーダルダイアログとして表示するかどうか
        """
        self.logger = LogManager().get_logger(self.__class__.__name__)
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.logger.debug(f"Initializing {self.__class__.__name__}: {title}")
        self.dialog.title(title)
        self.dialog.transient(parent)
        
        # モーダル設定
        if modal:
            self.dialog.grab_set()
        
        # イベントハンドラの辞書
        self._event_handlers: Dict[str, list] = {}
        
        # ダイアログが閉じられたときのクリーンアップ
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # スタイル設定
        self._setup_styles()
        
        # 画面中央に配置
        self._center_dialog()
    
    def _setup_styles(self):
        """スタイルの設定"""
        style = ttk.Style()
        
        # ボタンのスタイル
        if 'Dialog.TButton' not in style.theme_names():
            style.configure('Dialog.TButton', padding=5)
        
        # ラベルのスタイル
        if 'Dialog.TLabel' not in style.theme_names():
            style.configure('Dialog.TLabel', padding=2)
        
        # フレームのスタイル
        if 'Dialog.TFrame' not in style.theme_names():
            style.configure('Dialog.TFrame', padding=5)
    
    def _center_dialog(self) -> None:
        """ダイアログを親ウィンドウの中央に配置"""
        self.dialog.update_idletasks()
        
        # 親ウィンドウの位置とサイズを取得
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # ダイアログのサイズを取得
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 中央の位置を計算
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 位置を設定
        self.dialog.geometry(f"+{x}+{y}")
    
    def add_event_handler(self, event: str, handler: Callable) -> None:
        """
        イベントハンドラを追加
        
        Args:
            event: イベント名
            handler: ハンドラ関数
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def remove_event_handler(self, event: str, handler: Callable) -> None:
        """
        イベントハンドラを削除
        
        Args:
            event: イベント名
            handler: ハンドラ関数
        """
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
            except ValueError:
                pass
    
    def _trigger_event(self, event: str, **kwargs) -> None:
        """
        イベントを発火
        
        Args:
            event: イベント名
            **kwargs: イベントハンドラに渡す引数
        """
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(**kwargs)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {str(e)}")
    
    def _on_closing(self) -> None:
        """ダイアログが閉じられるときの処理"""
        try:
            # 登録されているイベントハンドラをクリア
            self._event_handlers.clear()
            
            # フォーカスを親ウィンドウに戻す
            self.parent.focus_set()
            
            # ダイアログを破棄
            self.dialog.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during dialog cleanup: {str(e)}")
    
    def show_error(self, message: str, title: str = "エラー") -> None:
        """エラーメッセージを表示"""
        messagebox.showerror(title, message, parent=self.dialog)
    
    def show_warning(self, message: str, title: str = "警告") -> None:
        """警告メッセージを表示"""
        messagebox.showwarning(title, message, parent=self.dialog)
    
    def show_info(self, message: str, title: str = "情報") -> None:
        """情報メッセージを表示"""
        messagebox.showinfo(title, message, parent=self.dialog)
    
    def ask_yes_no(self, message: str, title: str = "確認") -> bool:
        """
        はい/いいえの確認を表示
        
        Args:
            message: 確認メッセージ
            title: ダイアログのタイトル
        
        Returns:
            bool: はいが選択された場合True
        """
        return messagebox.askyesno(title, message, parent=self.dialog)
    
    def ask_ok_cancel(self, message: str, title: str = "確認") -> bool:
        """
        OK/キャンセルの確認を表示
        
        Args:
            message: 確認メッセージ
            title: ダイアログのタイトル
        
        Returns:
            bool: OKが選択された場合True
        """
        return messagebox.askokcancel(title, message, parent=self.dialog)