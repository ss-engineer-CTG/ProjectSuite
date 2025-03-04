# gui/main_window/project_frame.py

import tkinter as tk
from tkinter import ttk
from ..components.accordion import AccordionFrame

class ProjectFrame(ttk.Frame):
    """プロジェクト選択セクション"""
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
        self.project_var = tk.StringVar()
        self.project_info_var = tk.StringVar(value="プロジェクトが選択されていません")
        
        # UIの構築
        self.setup_ui()
    
    def setup_ui(self):
        """UIの構築"""
        # アコーディオンフレーム
        accordion = AccordionFrame(self, "プロジェクト選択", initial_state='open')
        accordion.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        content_frame = accordion.get_content_frame()
        
        # プロジェクト選択コンボボックス
        combo_frame = ttk.Frame(content_frame)
        combo_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        combo_frame.grid_columnconfigure(0, weight=1)
        
        self.project_combo = ttk.Combobox(
            combo_frame, 
            textvariable=self.project_var,
            state='disabled'
        )
        self.project_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.refresh_button = ttk.Button(
            combo_frame,
            text="更新",
            command=self.update_project_list,
            state='disabled'
        )
        self.refresh_button.grid(row=0, column=1)

        # プロジェクト情報表示
        info_frame = ttk.Frame(content_frame)
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        info_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(
            info_frame, 
            textvariable=self.project_info_var,
            wraplength=600
        ).grid(row=0, column=0, sticky=(tk.W, tk.E))

        # コンボボックスの選択イベントをバインド
        self.project_combo.bind('<<ComboboxSelected>>', self.on_project_selected)
        
        # グリッド設定
        self.grid_columnconfigure(0, weight=1)
    
    def update_project_list(self):
        """プロジェクト一覧の更新"""
        try:
            projects = self.processor.get_all_projects()
            project_values = [
                f"{p['project_id']}: {p['project_name']} ({p['start_date']})" 
                for p in projects
            ]
            
            self.project_combo['values'] = project_values
            
            # 最新プロジェクトの自動選択
            if projects and not self.project_var.get():
                self.project_combo.set(project_values[0])
                self.on_project_selected(None)
                
            self.enable()
            
        except Exception as e:
            self.disable()
            self.event_generate('<<Error>>', data=str(e))
    
    def on_project_selected(self, event=None):
        """プロジェクト選択時の処理"""
        if not self.project_var.get():
            return
            
        try:
            project_id = int(self.project_var.get().split(':')[0])
            project_data = self.processor.fetch_project_data(project_id)
            
            info_text = (
                f"プロジェクト名: {project_data['project_name']}\n"
                f"作成日: {project_data['start_date']}\n"
                f"工場: {project_data['factory']}\n"
                f"工程: {project_data['process']}\n"
                f"ライン: {project_data['line']}\n"
                f"作成者: {project_data['manager']}\n"
                f"確認者: {project_data['reviewer']}\n"
                f"承認者: {project_data['approver']}"
            )
            self.project_info_var.set(info_text)
            
            # プロジェクト選択イベントを発生
            self.event_generate('<<ProjectSelected>>')
            
        except Exception as e:
            self.event_generate('<<Error>>', data=str(e))
    
    def enable(self):
        """UI要素の有効化"""
        self.project_combo.configure(state='readonly')
        self.refresh_button.configure(state='normal')
    
    def disable(self):
        """UI要素の無効化"""
        self.project_combo.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        self.project_var.set('')
        self.project_info_var.set("プロジェクトが選択されていません")
    
    def get_selected_project_id(self) -> int:
        """
        選択されているプロジェクトIDを取得
        
        Returns:
            int: プロジェクトID
        """
        if not self.project_var.get():
            return None
        return int(self.project_var.get().split(':')[0])