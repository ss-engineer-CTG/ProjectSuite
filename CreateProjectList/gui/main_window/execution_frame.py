# gui/main_window/execution_frame.py

import tkinter as tk
from tkinter import ttk
from ..components.accordion import AccordionFrame
from pathlib import Path

class ExecutionFrame(ttk.Frame):
    """実行操作セクション"""
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
        self.input_folder_var = tk.StringVar(value="未設定")
        self.output_folder_var = tk.StringVar(value="未設定")
        
        # UIの構築
        self.setup_ui()
        self.update_folder_display()
        
    def setup_ui(self):
        """UIの構築"""
        # アコーディオンフレーム
        accordion = AccordionFrame(self, "実行操作", initial_state='closed')
        accordion.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        content_frame = accordion.get_content_frame()
        
        # 入力フォルダフレーム
        input_frame = ttk.Frame(content_frame)
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        input_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(input_frame, text="入力フォルダ:").grid(row=0, column=0, padx=(0, 10))
        ttk.Label(input_frame, textvariable=self.input_folder_var).grid(
            row=0, column=1, sticky=tk.W)
        ttk.Button(
            input_frame,
            text="選択",
            command=self.select_input_folder
        ).grid(row=0, column=2, padx=(10, 0))

        # 出力フォルダフレーム
        output_frame = ttk.Frame(content_frame)
        output_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        output_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="出力フォルダ:").grid(row=0, column=0, padx=(0, 10))
        ttk.Label(output_frame, textvariable=self.output_folder_var).grid(
            row=0, column=1, sticky=tk.W)
        ttk.Button(
            output_frame,
            text="選択",
            command=self.select_output_folder
        ).grid(row=0, column=2, padx=(10, 0))
        
        # グリッド設定
        self.grid_columnconfigure(0, weight=1)
    
    def select_input_folder(self):
        """入力フォルダの選択"""
        folder_path = tk.filedialog.askdirectory()
        if folder_path:
            self.processor.last_input_folder = folder_path
            self.update_folder_display()
            self.event_generate('<<FolderChanged>>')
    
    def select_output_folder(self):
        """出力フォルダの選択"""
        folder_path = tk.filedialog.askdirectory()
        if folder_path:
            self.processor.last_output_folder = folder_path
            self.update_folder_display()
            self.event_generate('<<FolderChanged>>')
    
    def update_folder_display(self):
        """フォルダパスの表示を更新"""
        if (self.processor.last_input_folder and 
            Path(self.processor.last_input_folder).exists()):
            self.input_folder_var.set(self.processor.last_input_folder)
        else:
            self.input_folder_var.set("未設定")

        if (self.processor.last_output_folder and 
            Path(self.processor.last_output_folder).exists()):
            self.output_folder_var.set(self.processor.last_output_folder)
        else:
            self.output_folder_var.set("未設定")