# gui/dialogs/database_viewer.py

import tkinter as tk
from tkinter import ttk
import sqlite3
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from .base_dialog import BaseDialog
from ..components.scrolled_frame import ScrolledFrame

class DatabaseViewer(BaseDialog):
    """データベースの内容を表示するビューワー"""
    
    def __init__(self, parent: tk.Tk, db_path: str):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            db_path: データベースファイルのパス
        """
        super().__init__(parent, "データベースビューワー")
        self.dialog.geometry("800x600")
        
        self.db_path = str(Path(db_path).resolve())
        self.current_table: Optional[str] = None
        self.current_connection: Optional[sqlite3.Connection] = None
        
        self.setup_gui()
        self.load_database()
    
    def setup_gui(self):
        """GUIの構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # テーブル選択部分
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(table_frame, text="テーブル:").grid(row=0, column=0, padx=5)
        self.table_combo = ttk.Combobox(table_frame, state='readonly', width=30)
        self.table_combo.grid(row=0, column=1, padx=5)
        self.table_combo.bind('<<ComboboxSelected>>', self.on_table_selected)

        # データ表示部分（直接フレームを使い、垂直・水平両方のスクロールバーを追加）
        data_frame = ttk.Frame(main_frame)
        data_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        data_frame.columnconfigure(0, weight=1)
        data_frame.rowconfigure(0, weight=1)

        # Treeviewの作成
        self.tree = ttk.Treeview(data_frame)
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 垂直スクロールバー
        vsb = ttk.Scrollbar(data_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=vsb.set)

        # 水平スクロールバー
        hsb = ttk.Scrollbar(data_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.tree.configure(xscrollcommand=hsb.set)

        # テーブル情報表示部分
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.table_info_var = tk.StringVar(value="")
        ttk.Label(info_frame, textvariable=self.table_info_var).grid(
            row=0, column=0, sticky=tk.W)

        # 検索フレーム
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(search_frame, text="検索:").grid(row=0, column=0, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.grid(row=0, column=1, padx=5)

        # グリッドの設定
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
    
    def load_database(self):
        """データベースの読み込み"""
        try:
            # データベースに接続
            self.current_connection = sqlite3.connect(self.db_path)
            self.logger.info(f"Database connected: {self.db_path}")
            cursor = self.current_connection.cursor()

            # テーブル一覧の取得
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name;
            """)
            tables = cursor.fetchall()
            
            # テーブル一覧をコンボボックスに設定
            self.table_combo['values'] = [table[0] for table in tables]
            if tables:
                self.table_combo.set(tables[0][0])
                self.load_table_data(tables[0][0])
            
        except sqlite3.Error as e:
            error_msg = f"データベースの読み込みに失敗しました: {str(e)}"
            self.logger.error(error_msg)
            self.show_error(error_msg)
            self._on_closing()
    
    def load_table_data(self, table_name: str):
        """
        テーブルデータの読み込み
        
        Args:
            table_name: テーブル名
        """
        try:
            cursor = self.current_connection.cursor()

            # テーブルのカラム情報を取得
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            column_types = [col[2] for col in columns]

            # データの取得
            cursor.execute(f"SELECT * FROM {table_name};")
            data = cursor.fetchall()

            # テーブル情報の表示
            self.update_table_info(table_name, len(data), columns)

            # Treeviewをリセット
            for item in self.tree.get_children():
                self.tree.delete(item)

            # カラムの設定
            self.tree['columns'] = column_names
            self.tree['show'] = 'headings'

            # カラム見出しの設定
            for col, col_type in zip(column_names, column_types):
                self.tree.heading(col, text=f"{col} ({col_type})")
                # カラム幅の設定（データ型に応じて）
                if 'INT' in col_type.upper() or 'REAL' in col_type.upper():
                    self.tree.column(col, width=80, anchor='e', stretch=False)
                elif 'DATE' in col_type.upper():
                    self.tree.column(col, width=100, anchor='center', stretch=False)
                else:
                    self.tree.column(col, width=150, anchor='w', stretch=False)

            # データの挿入
            for row in data:
                formatted_row = []
                for value, col_type in zip(row, column_types):
                    if value is None:
                        formatted_row.append('')
                    elif 'INT' in col_type.upper():
                        formatted_row.append(f"{value:,}")
                    elif 'REAL' in col_type.upper():
                        try:
                            # 小数点以下2桁で表示
                            formatted_row.append(f"{float(value):.2f}")
                        except (ValueError, TypeError):
                            formatted_row.append(str(value))
                    else:
                        formatted_row.append(str(value))
                self.tree.insert('', tk.END, values=formatted_row)
            
            # 現在のテーブル名を保存
            self.current_table = table_name
            
        except sqlite3.Error as e:
            self.show_error(f"テーブルデータの読み込みに失敗しました: {str(e)}")
    
    def update_table_info(self, table_name: str, row_count: int, columns: List[Tuple]):
        """
        テーブル情報の更新
        
        Args:
            table_name: テーブル名
            row_count: レコード数
            columns: カラム情報のリスト
        """
        primary_keys = [col[1] for col in columns if col[5]]  # col[5] は primary key フラグ
        info_text = (
            f"テーブル名: {table_name}\n"
            f"レコード数: {row_count:,}\n"
            f"カラム数: {len(columns)}\n"
        )
        if primary_keys:
            info_text += f"主キー: {', '.join(primary_keys)}"
        
        self.table_info_var.set(info_text)
    
    def on_table_selected(self, event):
        """テーブル選択時の処理"""
        selected_table = self.table_combo.get()
        if selected_table:
            self.load_table_data(selected_table)
            # 検索をクリア
            self.search_var.set("")
    
    def on_search_changed(self, *args):
        """検索文字列変更時の処理"""
        if not self.current_table:
            return
            
        search_text = self.search_var.get().lower()
        
        try:
            # すべての項目を一旦表示
            for item in self.tree.get_children():
                self.tree.item(item, tags=())
            
            if search_text:
                # 検索文字列に一致する項目をハイライト
                for item in self.tree.get_children():
                    values = [str(v).lower() for v in self.tree.item(item)['values']]
                    if any(search_text in value for value in values):
                        self.tree.item(item, tags=('found',))
                    else:
                        self.tree.item(item, tags=('hidden',))
                
                # スタイルの設定
                style = ttk.Style()
                style.configure('Treeview', rowheight=25)
                style.map('Treeview',
                    foreground=[('tag-hidden', 'gray')],
                    background=[('tag-found', '#e8f0fe')])
                
        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
    
    def _on_closing(self):
        """ダイアログが閉じられるときの処理"""
        if self.current_connection:
            try:
                self.current_connection.close()
            except sqlite3.Error as e:
                self.logger.error(f"Database close error: {str(e)}")
        
        super()._on_closing()