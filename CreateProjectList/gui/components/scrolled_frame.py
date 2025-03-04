# gui/components/scrolled_frame.py

import tkinter as tk
from tkinter import ttk

class ScrolledFrame(ttk.Frame):
    """スクロール可能なフレーム"""
    def __init__(self, parent, **kwargs):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
            **kwargs: フレームの追加設定
        """
        super().__init__(parent, **kwargs)
        
        # キャンバスとスクロールバーの作成
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content_frame = ttk.Frame(self.canvas)
        
        # キャンバスのスクロール設定
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # レイアウト
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # コンテンツフレームをキャンバスに配置
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.content_frame,
            anchor="nw"
        )
        
        # イベントバインド
        self.content_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # マウスホイールバインド
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        
    def _on_frame_configure(self, event=None):
        """フレームサイズが変更されたときの処理"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """キャンバスサイズが変更されたときの処理"""
        # コンテンツフレームの幅をキャンバスに合わせる
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """マウスホイールの処理"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _bind_mousewheel(self, event):
        """マウスホイールのバインド"""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        """マウスホイールのバインド解除"""
        self.canvas.unbind_all("<MouseWheel>")
    
    def get_content_frame(self) -> ttk.Frame:
        """
        コンテンツを配置するフレームを取得
        
        Returns:
            ttk.Frame: コンテンツフレーム
        """
        return self.content_frame