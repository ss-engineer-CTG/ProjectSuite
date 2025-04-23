"""プロジェクトパス設定ダイアログ"""

import os
import logging
import traceback
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
        self.window.title("プロジェクトフォルダ設定")
        self.window.transient(parent)
        self.window.grab_set()
        
        # ウィンドウの位置とサイズの設定
        window_width = 500
        window_height = 250
        x = parent.winfo_rootx() + (parent.winfo_width() - window_width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # フォント設定
        self.default_font = ("Meiryo", 12)
        self.header_font = ("Meiryo", 14, "bold")
        
        # 現在の設定を取得
        self.current_path = self.get_current_projects_path()
        
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
            text="プロジェクトフォルダの設定",
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
            text="プロジェクトフォルダ:",
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
    
    def get_current_projects_path(self) -> str:
        """
        現在のプロジェクトパスを取得
        
        Returns:
            str: 現在のプロジェクトパス
        """
        try:
            # PathRegistryからパスを取得
            from PathRegistry import PathRegistry
            registry = PathRegistry.get_instance()
            projects_dir = registry.get_path("PROJECTS_DIR")
            
            if projects_dir:
                return projects_dir
            
            # パスが未設定の場合のデフォルト
            return str(Path.home() / "Desktop" / "projects")
            
        except Exception as e:
            logging.error(f"プロジェクトパスの取得に失敗: {e}")
            return str(Path.home() / "Desktop" / "projects")
    
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
            messagebox.showwarning("警告", "プロジェクトフォルダが指定されていません。")
            return
        
        # パスの存在確認
        path_obj = Path(new_path)
        if not path_obj.exists():
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                logging.info(f"プロジェクトフォルダを作成しました: {path_obj}")
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
            # defaults.txtに設定を保存
            self.save_to_defaults_txt(new_path)
            
            # PathRegistryを更新
            from PathRegistry import PathRegistry
            registry = PathRegistry.get_instance()
            registry.register_path("PROJECTS_DIR", new_path)
            
            # 画面を閉じる
            self.window.destroy()
            
            # コールバックを呼び出す
            if self.callback:
                self.callback()
                
        except Exception as e:
            logging.error(f"設定の保存に失敗: {e}\n{traceback.format_exc()}")
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")
    
    def save_to_defaults_txt(self, projects_path: str) -> None:
        """
        defaults.txtに設定を保存
        
        Args:
            projects_path: プロジェクトフォルダのパス
        """
        try:
            # defaults.txtのパスを決定
            defaults_paths = [
                Path.home() / "Documents" / "ProjectSuite" / "defaults.txt",
                Path(__file__).parent.parent.parent.parent / "defaults.txt"
            ]
            
            # 最初に見つかったパスを使用
            defaults_file = None
            for path in defaults_paths:
                if path.exists():
                    defaults_file = path
                    break
            
            # ファイルが見つからない場合は作成
            if not defaults_file:
                defaults_file = defaults_paths[0]
                defaults_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 現在の設定を読み込む
            settings = {}
            if defaults_file.exists():
                with open(defaults_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                key, value = [x.strip() for x in line.split('=', 1)]
                                settings[key] = value
                            except ValueError:
                                continue
            
            # 設定を更新
            settings['custom_projects_dir'] = projects_path
            
            # 設定を保存
            with open(defaults_file, 'w', encoding='utf-8') as f:
                for key, value in settings.items():
                    f.write(f"{key}={value}\n")
            
            logging.info(f"設定を保存しました: {defaults_file}")
            
        except Exception as e:
            logging.error(f"defaults.txtへの保存に失敗: {e}")
            raise
    
    def on_close(self):
        """ダイアログを閉じる"""
        self.window.destroy()