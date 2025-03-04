# gui/dialogs/settings_dialog.py

import tkinter as tk
from tkinter import ttk, filedialog
import sqlite3
from pathlib import Path
from .base_dialog import BaseDialog
from .database_viewer import DatabaseViewer
from .rule_dialog import RuleDialog
from ..components.scrolled_frame import ScrolledFrame
from CreateProjectList.utils.path_manager import PathManager

class SettingsDialog(BaseDialog):
    """設定ダイアログ"""
    def __init__(self, parent: tk.Tk, processor):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            processor: DocumentProcessorインスタンス
        """
        super().__init__(parent, "設定")
        self.dialog.geometry("800x600")
        
        self.processor = processor
        self.is_db_connected = False
        self.settings_changed = False
        
        self.setup_dialog()
    
    def setup_dialog(self):
        """ダイアログの各部分をセットアップ"""
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ノートブック（タブ）の作成
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 各タブのフレーム
        db_frame = ttk.Frame(notebook, padding="5")
        rules_frame = ttk.Frame(notebook, padding="5")
        folder_frame = ttk.Frame(notebook, padding="5")
        
        # 各タブフレームのグリッド設定
        db_frame.grid_columnconfigure(0, weight=1)
        rules_frame.grid_columnconfigure(0, weight=1)
        folder_frame.grid_columnconfigure(0, weight=1)

        self.setup_database_tab(db_frame)
        self.setup_rules_tab(rules_frame)
        self.setup_folder_tab(folder_frame)

        notebook.add(db_frame, text="データベース設定")
        notebook.add(rules_frame, text="置換ルール")
        notebook.add(folder_frame, text="フォルダ設定")

        # 閉じるボタン
        button_frame = ttk.Frame(main_frame, padding="5")
        button_frame.grid(row=1, column=0, sticky=(tk.E, tk.S))
        ttk.Button(button_frame, text="閉じる", command=self._on_closing).pack(side=tk.RIGHT)

        # グリッド設定
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

    def setup_database_tab(self, parent):
        """データベース設定タブの内容をセットアップ"""
        # スクロール可能なフレームを使用
        scrolled_frame = ScrolledFrame(parent)
        scrolled_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame = scrolled_frame.get_content_frame()
        
        # データベースパス設定
        path_frame = ttk.Frame(frame)
        path_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        path_frame.columnconfigure(1, weight=1)  # パス表示部分を伸縮可能に
        
        ttk.Label(path_frame, text="データベースファイル:").grid(row=0, column=0, padx=5)
        
        self.db_path_var = tk.StringVar(value=self.processor.db_path)
        ttk.Entry(path_frame, textvariable=self.db_path_var, state='readonly', width=50).grid(
            row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        button_frame = ttk.Frame(path_frame)
        button_frame.grid(row=0, column=2, padx=5)
        
        ttk.Button(button_frame, text="DB選択", command=self.select_database).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="DBビューワー", command=self.open_db_viewer).pack(
            side=tk.LEFT, padx=2)

        # プロジェクト一覧
        ttk.Label(frame, text="登録済みプロジェクト一覧:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # プロジェクト一覧用のTreeview
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.project_tree = ttk.Treeview(
            tree_frame,
            columns=('id', 'name', 'date'),
            show='headings',
            height=10
        )
        
        self.project_tree.heading('id', text='ID')
        self.project_tree.heading('name', text='プロジェクト名')
        self.project_tree.heading('date', text='作成日')
        
        self.project_tree.column('id', width=50)
        self.project_tree.column('name', width=300)
        self.project_tree.column('date', width=100)
        
        self.project_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.project_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.project_tree.configure(yscrollcommand=scrollbar.set)

        # データベースの状態表示
        self.db_status_var = tk.StringVar(value="未接続")
        ttk.Label(frame, textvariable=self.db_status_var).grid(row=3, column=0, sticky=tk.W, pady=5)

        # 接続チェック
        ttk.Button(frame, text="接続テスト", command=self.test_database_connection).grid(
            row=4, column=0, sticky=tk.W, pady=5)

        # グリッド設定
        frame.columnconfigure(0, weight=1)

    def setup_rules_tab(self, parent):
        """置換ルール設定タブの内容をセットアップ"""
        # スクロール可能なフレームを使用
        scrolled_frame = ScrolledFrame(parent)
        scrolled_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame = scrolled_frame.get_content_frame()
        
        # 置換ルール一覧用のフレーム
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # 置換ルール一覧
        self.rules_tree = ttk.Treeview(
            tree_frame,
            columns=('search', 'replace'),
            show='headings',
            height=15
        )
        
        self.rules_tree.heading('search', text='検索文字列')
        self.rules_tree.heading('replace', text='置換後（DB参照キー）')
        self.rules_tree.column('search', width=300)
        self.rules_tree.column('replace', width=300)
        
        self.rules_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.rules_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.rules_tree.configure(yscrollcommand=scrollbar.set)
        
        # ボタン群
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, pady=5)
        
        ttk.Button(button_frame, text="追加", command=self.add_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="編集", command=self.edit_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="削除", command=self.delete_rule).pack(side=tk.LEFT, padx=5)

        # 初期データの読み込み
        self.load_rules()

        # グリッド設定
        frame.columnconfigure(0, weight=1)

    def setup_folder_tab(self, parent):
        """フォルダ設定タブの内容をセットアップ"""
        # スクロール可能なフレームを使用
        scrolled_frame = ScrolledFrame(parent)
        scrolled_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame = scrolled_frame.get_content_frame()

        # 入力フォルダ設定
        input_frame = ttk.LabelFrame(frame, text="入力フォルダ", padding="5")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        self.input_folder_var = tk.StringVar(value=self.processor.last_input_folder or "")
        ttk.Entry(input_frame, textvariable=self.input_folder_var, state='readonly').grid(
            row=0, column=0, padx=5, sticky=(tk.W, tk.E))
        
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="選択", command=self.select_input_folder).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="クリア", command=self.clear_input_folder).pack(
            side=tk.LEFT, padx=5)

        # 出力フォルダ設定
        output_frame = ttk.LabelFrame(frame, text="出力フォルダ", padding="5")
        output_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        self.output_folder_var = tk.StringVar(value=self.processor.last_output_folder or "")
        ttk.Entry(output_frame, textvariable=self.output_folder_var, state='readonly').grid(
            row=0, column=0, padx=5, sticky=(tk.W, tk.E))
        
        button_frame = ttk.Frame(output_frame)
        button_frame.grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="選択", command=self.select_output_folder).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="クリア", command=self.clear_output_folder).pack(
            side=tk.LEFT, padx=5)

        # グリッド設定
        frame.columnconfigure(0, weight=1)

    def select_database(self):
        """データベース選択ダイアログを表示"""
        try:
            db_path = filedialog.askopenfilename(
                parent=self.dialog,
                filetypes=[("SQLite files", "*.db")]
            )
            if not db_path:
                return
                
            normalized_path = PathManager.normalize_path(db_path)
            if not PathManager.is_valid_path(normalized_path):
                self.show_error("無効なパスが指定されました。")
                return
                
            self.processor.db_path = normalized_path
            self.db_path_var.set(normalized_path)
            self.test_database_connection()
            self.settings_changed = True
            
        except Exception as e:
            self.show_error(f"データベースの設定に失敗しました: {str(e)}")
            self.logger.error(f"Database setting error: {str(e)}")

    def test_database_connection(self):
        """データベース接続テスト"""
        try:
            if self.processor.db_context and self.processor.db_context.test_connection():
                self.processor.is_db_connected = True
                self.update_project_list()
                self.db_status_var.set("接続済み")
                self.show_info("データベースの接続に成功しました。")
            else:
                self.processor.is_db_connected = False
                self.db_status_var.set("接続エラー")
                self.show_error("接続エラー", "データベースに接続できません。")
        except Exception as e:
            self.processor.is_db_connected = False
            error_msg = f"データベース接続エラー: {str(e)}"
            self.logger.error(error_msg)
            self.show_error(error_msg)
            self.db_status_var.set("接続エラー")

    def open_db_viewer(self):
        """データベースビューワーを開く"""
        try:
            if not self.processor.db_path:
                self.show_warning("データベースが選択されていません。")
                return
            
            DatabaseViewer(self.dialog, self.processor.db_path)
        except Exception as e:
            self.show_error(f"データベースビューワーの起動に失敗しました: {str(e)}")
            self.logger.error(f"Database viewer error: {str(e)}")

    def update_project_list(self):
        """プロジェクト一覧の更新"""
        try:
            for item in self.project_tree.get_children():
                self.project_tree.delete(item)
            
            if not self.is_db_connected:
                return
                
            projects = self.processor.get_all_projects()
            
            for project in projects:
                self.project_tree.insert(
                    '', 'end',
                    values=(
                        project['project_id'],
                        project['project_name'],
                        project['start_date']
                    )
                )
                
        except Exception as e:
            self.show_error(f"プロジェクト一覧の取得に失敗しました: {str(e)}")
            self.logger.error(f"Project list update error: {str(e)}")

    def load_rules(self):
        """置換ルールの読み込み"""
        try:
            for item in self.rules_tree.get_children():
                self.rules_tree.delete(item)
            
            for rule in self.processor.replacement_rules:
                self.rules_tree.insert('', 'end', values=(rule["search"], rule["replace"]))
        except Exception as e:
            self.show_error(f"置換ルールの読み込みに失敗しました: {str(e)}")
            self.logger.error(f"Rule loading error: {str(e)}")

    def add_rule(self):
        """置換ルールの追加"""
        try:
            dialog = RuleDialog(self.dialog, "置換ルールの追加")
            self.dialog.wait_window(dialog.dialog)
            
            if dialog.result:
                # 重複チェック
                for existing_rule in self.processor.replacement_rules:
                    if existing_rule["search"] == dialog.result["search"]:
                        self.show_error("この検索文字列は既に登録されています。")
                        return
                
                self.processor.replacement_rules.append(dialog.result)
                self.load_rules()
                self.settings_changed = True
        except Exception as e:
            self.show_error(f"置換ルールの追加に失敗しました: {str(e)}")
            self.logger.error(f"Rule addition error: {str(e)}")

    def edit_rule(self):
        """置換ルールの編集"""
        try:
            selected = self.rules_tree.selection()
            if not selected:
                self.show_warning("編集するルールを選択してください。")
                return

            item = selected[0]
            values = self.rules_tree.item(item)['values']
            current_rule = {"search": values[0], "replace": values[1]}
            
            dialog = RuleDialog(self.dialog, "置換ルールの編集", current_rule)
            self.dialog.wait_window(dialog.dialog)
            
            if dialog.result:
                # 既存のルールを更新
                rule_index = next(
                    i for i, rule in enumerate(self.processor.replacement_rules)
                    if rule["search"] == current_rule["search"] and rule["replace"] == current_rule["replace"]
                )
                self.processor.replacement_rules[rule_index] = dialog.result
                self.load_rules()
                self.settings_changed = True
        except Exception as e:
            self.show_error(f"置換ルールの編集に失敗しました: {str(e)}")
            self.logger.error(f"Rule editing error: {str(e)}")

    def delete_rule(self):
        """置換ルールの削除"""
        try:
            selected = self.rules_tree.selection()
            if not selected:
                self.show_warning("削除するルールを選択してください。")
                return

            if self.ask_yes_no("選択したルールを削除してもよろしいですか？"):
                item = selected[0]
                values = self.rules_tree.item(item)['values']
                current_rule = {"search": values[0], "replace": values[1]}
                
                self.processor.replacement_rules = [
                    rule for rule in self.processor.replacement_rules
                    if not (rule["search"] == current_rule["search"] and rule["replace"] == current_rule["replace"])
                ]
                
                self.load_rules()
                self.settings_changed = True
        except Exception as e:
            self.show_error(f"置換ルールの削除に失敗しました: {str(e)}")
            self.logger.error(f"Rule deletion error: {str(e)}")

    def select_input_folder(self):
        """入力フォルダの選択"""
        try:
            folder_path = filedialog.askdirectory(parent=self.dialog)
            if folder_path:
                normalized_path = PathManager.normalize_path(folder_path)
                if not PathManager.is_valid_path(normalized_path):
                    self.show_error("無効なパスが指定されました。")
                    return
                    
                self.processor.last_input_folder = normalized_path
                self.input_folder_var.set(normalized_path)
                self.settings_changed = True
        except Exception as e:
            self.show_error(f"フォルダの選択に失敗しました: {str(e)}")
            self.logger.error(f"Input folder selection error: {str(e)}")

    def select_output_folder(self):
        """出力フォルダの選択"""
        try:
            folder_path = filedialog.askdirectory(parent=self.dialog)
            if folder_path:
                normalized_path = PathManager.normalize_path(folder_path)
                if not PathManager.is_valid_path(normalized_path):
                    self.show_error("無効なパスが指定されました。")
                    return
                    
                self.processor.last_output_folder = normalized_path
                self.output_folder_var.set(normalized_path)
                self.settings_changed = True
        except Exception as e:
            self.show_error(f"フォルダの選択に失敗しました: {str(e)}")
            self.logger.error(f"Output folder selection error: {str(e)}")

    def clear_input_folder(self):
        """入力フォルダパスをクリア"""
        try:
            if self.ask_yes_no("入力フォルダの設定をクリアしてもよろしいですか？"):
                self.processor.last_input_folder = ""
                self.input_folder_var.set("")
                self.settings_changed = True
        except Exception as e:
            self.show_error(f"フォルダのクリアに失敗しました: {str(e)}")
            self.logger.error(f"Input folder clear error: {str(e)}")

    def clear_output_folder(self):
        """出力フォルダパスをクリア"""
        try:
            if self.ask_yes_no("出力フォルダの設定をクリアしてもよろしいですか？"):
                self.processor.last_output_folder = ""
                self.output_folder_var.set("")
                self.settings_changed = True
        except Exception as e:
            self.show_error(f"フォルダのクリアに失敗しました: {str(e)}")
            self.logger.error(f"Output folder clear error: {str(e)}")

    def _on_closing(self):
        """ダイアログを閉じる"""
        try:
            if self.settings_changed:
                self.dialog.event_generate("<<SettingsChanged>>")
            super()._on_closing()
        except Exception as e:
            self.logger.error(f"Dialog closing error: {str(e)}")
            self.dialog.destroy()