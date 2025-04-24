"""プロジェクトパス設定ダイアログ"""

import os
import json
import logging
from pathlib import Path
from typing import Callable, Optional
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

class ProjectPathDialog:
    """プロジェクトパス設定ダイアログ"""
    
    def __init__(self, parent, callback: Optional[Callable] = None):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            callback: 設定変更後のコールバック
        """
        self.callback = callback
        
        # ダイアログの作成
        self.window = ctk.CTkToplevel(parent)
        self.window.title("プロジェクトデータの保存先設定")
        self.window.transient(parent)
        self.window.grab_set()
        
        # ウィンドウの位置とサイズの設定
        window_width = 500
        window_height = 280
        x = parent.winfo_rootx() + (parent.winfo_width() - window_width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # フォント設定
        self.default_font = ("Meiryo", 12)
        self.header_font = ("Meiryo", 14, "bold")
        
        # 現在の設定を取得
        self.current_path = self.get_current_output_dir()
        
        # UIの構築
        self.setup_ui()
        
        # 閉じるボタンが押された時の処理
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_ui(self):
        """UIの構築"""
        main_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ヘッダー
        header_label = ctk.CTkLabel(
            main_frame,
            text="プロジェクトデータの保存先設定",
            font=self.header_font
        )
        header_label.pack(pady=(0, 20))
        
        # 説明
        description = (
            "プロジェクトのデータが保存されるフォルダを選択してください。\n"
            "既存のプロジェクトは自動的に移行されません。"
        )
        desc_label = ctk.CTkLabel(
            main_frame,
            text=description,
            font=self.default_font,
            wraplength=450
        )
        desc_label.pack(pady=(0, 20))
        
        # パス入力フレーム
        path_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=10)
        
        path_label = ctk.CTkLabel(
            path_frame,
            text="保存先フォルダ:",
            font=self.default_font,
            width=140
        )
        path_label.pack(side="left")
        
        self.path_var = tk.StringVar(value=self.current_path or "")
        path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.path_var,
            font=self.default_font,
            width=250
        )
        path_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        browse_button = ctk.CTkButton(
            path_frame,
            text="参照...",
            font=self.default_font,
            width=80,
            command=self.browse_directory
        )
        browse_button.pack(side="left")
        
        # 注意書き
        warning_text = (
            "注意: 変更を適用するにはアプリケーションの再起動が必要です。\n"
            "既存のプロジェクトデータを新しいフォルダに手動で移行してください。"
        )
        warning_label = ctk.CTkLabel(
            main_frame,
            text=warning_text,
            font=("Meiryo", 10),
            text_color="red",
            wraplength=450
        )
        warning_label.pack(pady=10)
        
        # 現在の設定情報
        current_info = f"現在の設定: {self.current_path}"
        info_label = ctk.CTkLabel(
            main_frame,
            text=current_info,
            font=("Meiryo", 10),
            text_color="gray",
            wraplength=450
        )
        info_label.pack(pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=10)
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="キャンセル",
            font=self.default_font,
            width=100,
            command=self.on_close
        )
        cancel_button.pack(side="right", padx=5)
        
        save_button = ctk.CTkButton(
            button_frame,
            text="保存",
            font=self.default_font,
            width=100,
            command=self.save_settings
        )
        save_button.pack(side="right", padx=5)
    
    def get_current_output_dir(self) -> str:
        """
        現在の出力ディレクトリを取得
        
        Returns:
            str: 現在の出力ディレクトリパス
        """
        try:
            # PathRegistryからパスを取得
            from PathRegistry import PathRegistry
            registry = PathRegistry.get_instance()
            
            # OUTPUT_BASE_DIRを優先して取得
            output_dir = registry.get_path("OUTPUT_BASE_DIR")
            if output_dir:
                return output_dir
                
            # 後方互換性のためにPROJECTS_DIRも確認
            projects_dir = registry.get_path("PROJECTS_DIR")
            if projects_dir:
                return projects_dir
            
            # パスが未設定の場合のデフォルト
            return str(Path.home() / "Documents" / "ProjectSuite" / "ProjectManager" / "data" / "projects")
            
        except Exception as e:
            logging.error(f"出力ディレクトリの取得に失敗: {e}")
            return str(Path.home() / "Documents" / "ProjectSuite" / "ProjectManager" / "data" / "projects")
    
    def browse_directory(self):
        """フォルダ選択ダイアログを表示"""
        initial_dir = self.path_var.get() if Path(self.path_var.get()).exists() else str(Path.home())
        directory = filedialog.askdirectory(initialdir=initial_dir)
        
        if directory:
            self.path_var.set(directory)
    
    def save_settings(self):
        """設定を保存"""
        new_path = self.path_var.get()
        
        if not new_path:
            messagebox.showwarning("警告", "保存先フォルダが指定されていません。")
            return
        
        # パスの存在確認
        path_obj = Path(new_path)
        if not path_obj.exists():
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                logging.info(f"出力フォルダを作成しました: {path_obj}")
            except Exception as e:
                messagebox.showerror("エラー", f"フォルダの作成に失敗しました: {e}")
                return
        
        # 書き込み権限のチェック
        try:
            test_file = path_obj / '.write_test'
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            messagebox.showerror("エラー", f"フォルダへの書き込み権限がありません: {e}")
            return
        
        try:
            # PathRegistryを更新
            from PathRegistry import PathRegistry
            registry = PathRegistry.get_instance()
            
            # 出力ディレクトリを更新
            registry.update_output_dir(new_path)
            
            # ConfigManagerも利用可能なら更新
            try:
                from ProjectManager.src.core.config_manager import ConfigManager
                config_manager = ConfigManager()
                config_manager.update_output_dir(new_path)
            except ImportError:
                pass
            
            # 画面を閉じる
            self.window.destroy()
            
            # コールバックを呼び出す
            if self.callback:
                self.callback()
                
            messagebox.showinfo(
                "保存完了", 
                "保存先フォルダを更新しました。\n設定を完全に適用するには、アプリケーションを再起動してください。"
            )
                
        except Exception as e:
            logging.error(f"設定の保存に失敗: {e}")
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")
    
    def on_close(self):
        """ダイアログを閉じる"""
        self.window.destroy()