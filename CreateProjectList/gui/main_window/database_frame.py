# gui/main_window/database_frame.py

import tkinter as tk
from tkinter import ttk
from ..components.accordion import AccordionFrame

class DatabaseFrame(ttk.Frame):
    """データベース状態セクション"""
    def __init__(self, parent, processor):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
            processor: DocumentProcessorインスタンス
        """
        super().__init__(parent)
        self.processor = processor
        
        # 変数の初期化
        self.db_path_var = tk.StringVar(value="未設定")
        self.db_status_var = tk.StringVar(value="未接続")
        
        # UIの構築
        self.setup_ui()
        self.update_status()
    
    def setup_ui(self):
        """UIの構築"""
        # アコーディオンフレーム
        accordion = AccordionFrame(self, "データベース状態", initial_state='closed')
        accordion.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        content_frame = accordion.get_content_frame()
        
        # パス表示
        path_frame = ttk.Frame(content_frame)
        path_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        path_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(path_frame, text="接続先:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(path_frame, textvariable=self.db_path_var).grid(
            row=0, column=1, sticky=tk.W)
        
        # 状態表示
        status_frame = ttk.Frame(content_frame)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        status_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="状態:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(status_frame, textvariable=self.db_status_var).grid(
            row=0, column=1, sticky=tk.W)
        
        # グリッド設定
        self.grid_columnconfigure(0, weight=1)
    
    def update_status(self):
        """状態表示の更新"""
        if self.processor.db_path:
            self.db_path_var.set(self.processor.db_path)
            if self.processor.is_db_connected:
                self.db_status_var.set("接続済み")
            else:
                self.db_status_var.set("未接続")
        else:
            self.db_path_var.set("未設定")
            self.db_status_var.set("未接続")