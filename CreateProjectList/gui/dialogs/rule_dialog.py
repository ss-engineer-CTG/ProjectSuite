# gui/dialogs/rule_dialog.py

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict
from .base_dialog import BaseDialog

class RuleDialog(BaseDialog):
    """置換ルールの追加・編集用ダイアログ"""
    
    def __init__(self, parent: tk.Tk, title: str, rule: Optional[Dict[str, str]] = None):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            title: ダイアログのタイトル
            rule: 既存のルール（編集時）
        """
        super().__init__(parent, title)
        self.result = None
        self.rule = rule or {"search": "", "replace": ""}
        self.setup_dialog()

    def setup_dialog(self):
        """ダイアログの構築"""
        # 入力フレーム
        input_frame = ttk.Frame(self.dialog, padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 検索文字列
        ttk.Label(input_frame, text="検索文字列:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.search_var = tk.StringVar(value=self.rule["search"])
        self.search_entry = ttk.Entry(input_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        # 置換後文字列
        ttk.Label(input_frame, text="置換後（DB参照キー）:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.replace_var = tk.StringVar(value=self.rule["replace"])
        self.replace_entry = ttk.Entry(input_frame, textvariable=self.replace_var, width=40)
        self.replace_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)

        # 参照キー一覧
        ttk.Label(input_frame, text="利用可能な参照キー:").grid(row=2, column=0, sticky=tk.W, pady=5)
        reference_text = (
            "project_name: 案件名\n"
            "start_date: 作成日\n"
            "factory: 工場\n"
            "process: 工程\n"
            "line: ライン\n"
            "manager: 作成者\n"
            "reviewer: 確認者\n"
            "approver: 承認者\n"
            "division: 事業部"
        )
        reference_label = ttk.Label(
            input_frame,
            text=reference_text,
            justify=tk.LEFT,
            font=('Courier', 9)
        )
        reference_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)

        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog, padding="10")
        button_frame.grid(row=1, column=0, sticky=(tk.E, tk.S))

        ttk.Button(button_frame, text="保存", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

        # グリッド設定
        input_frame.grid_columnconfigure(1, weight=1)

    def save(self):
        """ルールの保存"""
        if not self.search_var.get() or not self.replace_var.get():
            self.show_error("検索文字列と置換後文字列を入力してください。")
            return
        
        self.result = {
            "search": self.search_var.get(),
            "replace": self.replace_var.get()
        }
        self._on_closing()

    def cancel(self):
        """ダイアログのキャンセル"""
        self._on_closing()