# gui/components/accordion.py

import tkinter as tk
from tkinter import ttk

class AccordionFrame(ttk.LabelFrame):
    """アコーディオンパネル実装"""
    def __init__(self, parent, title: str, initial_state: str = 'closed', **kwargs):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
            title: パネルのタイトル
            initial_state: 初期状態 ('open' or 'closed')
        """
        super().__init__(parent, text=title, **kwargs)
        
        self.is_expanded = initial_state == 'open'
        
        # ヘッダーフレーム
        self.header_frame = ttk.Frame(self)
        self.header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        # トグルボタン
        self.toggle_button = ttk.Button(
            self.header_frame,
            text="▼" if self.is_expanded else "▶",
            width=3,
            command=self.toggle,
            style='Accordion.TButton'
        )
        self.toggle_button.grid(row=0, column=0, padx=(0, 5))
        
        # コンテンツフレーム
        self.content_frame = ttk.Frame(self, padding=(10, 5, 10, 5))
        if self.is_expanded:
            self.content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # グリッド設定
        self.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # スタイル設定
        style = ttk.Style()
        if 'Accordion.TButton' not in style.theme_names():
            style.configure('Accordion.TButton', padding=1)
    
    def toggle(self) -> None:
        """パネルの展開/折りたたみを切り替え"""
        if self.is_expanded:
            self.content_frame.grid_remove()
            self.toggle_button.configure(text="▶")
        else:
            self.content_frame.grid(
                row=1, column=0, 
                sticky=(tk.W, tk.E, tk.N, tk.S), 
                padx=5, pady=5
            )
            self.toggle_button.configure(text="▼")
        self.is_expanded = not self.is_expanded
    
    def get_content_frame(self) -> ttk.Frame:
        """
        コンテンツを配置するフレームを取得
        
        Returns:
            ttk.Frame: コンテンツフレーム
        """
        return self.content_frame