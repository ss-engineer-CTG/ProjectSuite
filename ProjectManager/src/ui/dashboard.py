"""ダッシュボードGUIクラス"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime

from ProjectManager.src.ui.project.quick_form import QuickProjectForm
from ProjectManager.src.ui.project.detail_form import DetailProjectForm
from ProjectManager.src.core.config import Config
from ProjectManager.src.services.gantt_updater import GanttChartUpdater
from ProjectManager.src.services.task_loader import TaskLoader
from ProjectManager.src.ui.styles.color_scheme import ColorScheme
from ProjectManager.src.integration.document_processor_manager import DocumentProcessorManager
from CreateProjectList.gui.main_window.document_processor_gui import DocumentProcessorGUI

class DashboardGUI:
    """ダッシュボードGUIクラス"""
    
    def __init__(self, db_manager):
        """
        ダッシュボードGUIの初期化
        
        Args:
            db_manager: データベースマネージャーインスタンス
        """
        self.is_closing = False
        self.db_manager = db_manager
        self.current_filter = "進行中"
        self.colors = ColorScheme
        
        # 選択中のプロジェクト
        self.selected_project = None
        self.selected_project_frame = None
        self.selected_info = None
        
        # ドキュメント処理マネージャー
        self.doc_processor_manager = None
        
        # フォント設定
        self.default_font = ("Meiryo", 12)
        self.header_font = ("Meiryo", 14, "bold")
        self.title_font = ("Meiryo", 20, "bold")
        
        # CustomTkinterのテーマ設定
        ctk.set_appearance_mode("dark")
        
        # メインウィンドウの設定
        self.window = None
        self.initialize_window()
        
        # プロジェクト作成ダイアログのインスタンス
        self.project_dialog = None
        
        # 現在のプロジェクトリスト
        self.project_list = []
        
        # プロジェクトの表示を更新
        self.refresh_projects()
        
        # ドキュメント処理マネージャーの初期化
        self.initialize_doc_processor()
        
        logging.info("ダッシュボードGUIを初期化しました")

    def initialize_window(self):
        """ウィンドウの初期化"""
        self.window = ctk.CTk()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.configure(fg_color=self.colors.BACKGROUND)
        self.setup_main_window()

    def initialize_doc_processor(self):
        """ドキュメント処理マネージャーの初期化"""
        try:
            config = {
                'base_dir': str(Config.DATA_DIR),
                'db_path': str(Config.DB_PATH),
                'master_dir': str(Config.MASTER_DIR),
                'output_dir': str(Config.get_output_base_dir())
            }
            self.doc_processor_manager = DocumentProcessorManager(config)
            logging.info("ドキュメント処理マネージャーを初期化しました")
        except Exception as e:
            logging.error(f"ドキュメント処理マネージャーの初期化エラー: {e}")
            messagebox.showerror("エラー", "ドキュメント処理機能の初期化に失敗しました。")

    def setup_main_window(self):
        """メインウィンドウ（ダッシュボード）の設定"""
        self.window.title("プロジェクト管理ダッシュボード")
        
        # スクリーンサイズの取得と設定
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # ウィンドウを中央に配置
        # x = (screen_width - window_width) // 2
        # y = (screen_height - window_height) // 2
        x = 0
        y = 0
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # メインフレーム
        main_frame = ctk.CTkFrame(
            self.window,
            fg_color=self.colors.BACKGROUND
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ヘッダーフレーム
        header_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.colors.CARD_BG
        )
        header_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # タイトル
        title_label = ctk.CTkLabel(
            header_frame,
            text="プロジェクト一覧",
            font=self.title_font,
            text_color=self.colors.TEXT_PRIMARY
        )
        title_label.pack(side="left", pady=10, padx=10)

        # フィルターフレーム
        filter_frame = ctk.CTkFrame(
            header_frame,
            fg_color=self.colors.CARD_BG
        )
        filter_frame.pack(side="right", pady=10, padx=10)
        
        # フィルターラベル
        filter_label = ctk.CTkLabel(
            filter_frame,
            text="表示フィルター:",
            font=self.default_font,
            text_color=self.colors.TEXT_PRIMARY
        )
        filter_label.pack(side="left", padx=(0, 10))
        
        # フィルターコンボボックス
        self.filter_combo = ctk.CTkComboBox(
            filter_frame,
            values=['進行中', '全て'],
            command=self.on_filter_change,
            state="readonly",
            font=self.default_font,
            fg_color=self.colors.INPUT_BG,
            text_color=self.colors.INPUT_TEXT,
            border_color=self.colors.INPUT_BORDER,
            button_color=self.colors.BUTTON_PRIMARY,
            button_hover_color=self.colors.BUTTON_HOVER,
            dropdown_fg_color=self.colors.CARD_BG,
            width=120
        )
        self.filter_combo.set('進行中')
        self.filter_combo.pack(side="left", padx=(0, 10))
        
        # データベース更新ボタン
        update_button = ctk.CTkButton(
            filter_frame,
            text="データベース更新",
            command=self.update_ganttchart_paths,
            font=self.default_font,
            fg_color=self.colors.BUTTON_PRIMARY,
            text_color=self.colors.BUTTON_TEXT,
            hover_color=self.colors.BUTTON_HOVER,
            width=150
        )
        update_button.pack(side="left", padx=(0, 10))
        
        # 設定ボタン
        settings_button = ctk.CTkButton(
            filter_frame,
            text="設定",
            command=self.show_settings_dialog,
            font=self.default_font,
            fg_color=self.colors.BUTTON_PRIMARY,
            text_color=self.colors.BUTTON_TEXT,
            hover_color=self.colors.BUTTON_HOVER,
            width=80
        )
        settings_button.pack(side="left", padx=(0, 10))
        
        # ドキュメント処理ボタン
        doc_process_button = ctk.CTkButton(
            filter_frame,
            text="ドキュメント処理",
            command=self.show_document_processor,
            font=self.default_font,
            fg_color=self.colors.BUTTON_PRIMARY,
            text_color=self.colors.BUTTON_TEXT,
            hover_color=self.colors.BUTTON_HOVER,
            width=150
        )
        doc_process_button.pack(side="left", padx=(0, 10))

        # プロジェクト進捗ダッシュボードボタン
        dashboard_button = ctk.CTkButton(
            filter_frame,  # または適切なフレーム（ドキュメント処理ボタンと同じフレーム）
            text="進捗ダッシュボード",
            command=self.launch_project_dashboard,
            font=self.default_font,
            fg_color=self.colors.BUTTON_PRIMARY,
            text_color=self.colors.BUTTON_TEXT,
            hover_color=self.colors.BUTTON_HOVER,
            width=150
        )
        dashboard_button.pack(side="left", padx=(0, 10))
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(
            header_frame,
            fg_color=self.colors.CARD_BG
        )
        button_frame.pack(side="right", pady=10, padx=10)
        
        # 新規プロジェクト作成ボタン
        create_button = ctk.CTkButton(
            button_frame,
            text="新規プロジェクト作成",
            command=self.show_create_project_dialog,
            font=self.default_font,
            fg_color=self.colors.BUTTON_PRIMARY,
            text_color=self.colors.BUTTON_TEXT,
            hover_color=self.colors.BUTTON_HOVER
        )
        create_button.pack(side="right")

        # 選択中プロジェクト表示セクション
        self.selected_project_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.colors.CARD_BG,
            height=100
        )
        self.selected_project_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # タイトル
        selected_title = ctk.CTkLabel(
            self.selected_project_frame,
            text="選択中のプロジェクト",
            font=self.header_font,
            text_color=self.colors.TEXT_PRIMARY
        )
        selected_title.pack(side="left", pady=10, padx=10)
        
        # 選択中プロジェクト情報
        self.selected_info = ctk.CTkLabel(
            self.selected_project_frame,
            text="プロジェクトが選択されていません",
            font=self.default_font,
            text_color=self.colors.TEXT_SECONDARY
        )
        self.selected_info.pack(side="left", pady=10, padx=10)
        
        # プロジェクト一覧を表示するスクロール可能なフレーム
        self.projects_frame = ctk.CTkScrollableFrame(
            main_frame,
            label_text="",
            fg_color=self.colors.BACKGROUND,
            scrollbar_button_color=self.colors.SCROLLBAR_FG,
            scrollbar_button_hover_color=self.colors.get_hover_color(self.colors.SCROLLBAR_FG)
        )
        self.projects_frame._scrollbar.configure(
            button_color=self.colors.SCROLLBAR_FG,
            button_hover_color=self.colors.get_hover_color(self.colors.SCROLLBAR_FG)
        )
        if hasattr(self.projects_frame, '_label'):
            self.projects_frame._label.configure(
                font=self.header_font,
                text_color=self.colors.TEXT_PRIMARY
            )
        self.projects_frame.pack(fill="both", expand=True, padx=20)

        self.main_frame = main_frame

    def show_settings_dialog(self):
        """設定ダイアログを表示"""
        try:
            from ProjectManager.src.ui.project_path_dialog import ProjectPathDialog
            ProjectPathDialog(self.window, self.on_settings_changed)
        except Exception as e:
            logging.error(f"設定ダイアログの表示に失敗しました: {e}")
            messagebox.showerror("エラー", f"設定ダイアログの表示に失敗しました: {e}")

    def on_settings_changed(self):
        """設定変更後のコールバック"""
        try:
            # 必要に応じてパスの再読み込みや画面更新を行う
            logging.info("設定が変更されました。アプリケーションの再起動が必要です。")
            messagebox.showinfo(
                "設定変更",
                "プロジェクトフォルダ設定を変更しました。\n"
                "変更を完全に適用するには、アプリケーションを再起動してください。"
            )
        except Exception as e:
            logging.error(f"設定変更の適用に失敗しました: {e}")
            messagebox.showerror("エラー", f"設定変更の適用に失敗しました: {e}")

    def create_project_card(self, project):
        """
        プロジェクトカードの作成
        
        Args:
            project: プロジェクトデータ
        """
        # カードフレーム
        card = ctk.CTkFrame(
            self.projects_frame,
            fg_color=self.colors.CARD_BG,
            border_color=self.colors.FRAME_BORDER,
            border_width=1
        )
        card.pack(fill="x", padx=10, pady=5)
        
        # カードをクリック可能にする
        for widget in [card]:
            widget.bind('<Button-1>', lambda e, p=project: self.select_project(p))
        
        # 選択状態の表示
        if self.selected_project and self.selected_project['project_id'] == project['project_id']:
            card.configure(border_color=self.colors.BUTTON_PRIMARY, border_width=2)
            
        # 左側の情報フレーム
        info_frame = ctk.CTkFrame(
            card,
            fg_color=self.colors.CARD_BG
        )
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        info_frame.bind('<Button-1>', lambda e, p=project: self.select_project(p))
        
        # 現在のステータスを取得
        current_status = project.get('status', '進行中')
        
        # ステータスバッジ
        status_frame = ctk.CTkFrame(
            info_frame,
            fg_color=self.colors.STATUS[current_status]
        )
        status_frame.pack(side="right", padx=5)
        status_frame.bind('<Button-1>', lambda e, p=project: self.select_project(p))
        
        status_label = ctk.CTkLabel(
            status_frame,
            text=current_status,
            text_color=self.colors.BUTTON_TEXT,
            font=('Meiryo', 10, 'bold')
        )
        status_label.pack(padx=8, pady=4)
        status_label.bind('<Button-1>', lambda e, p=project: self.select_project(p))
        
        # プロジェクト名
        name_label = ctk.CTkLabel(
            info_frame,
            text=f"プロジェクト名: {project['project_name']}",
            font=self.header_font,
            text_color=self.colors.TEXT_PRIMARY,
            anchor="w"
        )
        name_label.pack(fill="x")
        name_label.bind('<Button-1>', lambda e, p=project: self.select_project(p))
        
        # NULL値の場合は "未設定" と表示する関数
        def get_display_value(value):
            return value if value is not None else "未設定"
        
        # 基本情報テキスト
        info_text = (
            f"開始日: {project['start_date']} | "
            f"担当者: {project['manager']} | "
            f"確認者: {project['reviewer']} | "
            f"承認者: {project['approver']} | "
            f"事業部: {get_display_value(project['division'])} | "
            f"工場: {get_display_value(project['factory'])} | "
            f"工程: {get_display_value(project['process'])} | "
            f"ライン: {get_display_value(project['line'])}"
        )
        
        details_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=self.default_font,
            text_color=self.colors.TEXT_SECONDARY,
            anchor="w"
        )
        details_label.pack(fill="x", pady=(5, 0))
        details_label.bind('<Button-1>', lambda e, p=project: self.select_project(p))
        
        # 右側のボタンフレーム
        button_frame = ctk.CTkFrame(
            card,
            fg_color=self.colors.CARD_BG
        )
        button_frame.pack(side="right", padx=10, pady=10)
        
        # 編集ボタン
        edit_button = ctk.CTkButton(
            button_frame,
            text="編集",
            command=lambda: self.edit_project(project['project_id']),
            font=self.default_font,
            fg_color=self.colors.BUTTON_PRIMARY,
            text_color=self.colors.BUTTON_TEXT,
            hover_color=self.colors.BUTTON_HOVER,
            width=100
        )
        edit_button.pack(pady=(0, 5))
        
        # 削除ボタン
        delete_button = ctk.CTkButton(
            button_frame,
            text="削除",
            command=lambda: self.delete_project(project['project_id']),
            font=self.default_font,
            fg_color=self.colors.BUTTON_DANGER,
            hover_color='#CC2F26',
            width=100
        )
        delete_button.pack()

    def select_project(self, project):
        """
        プロジェクトの選択
        
        Args:
            project: 選択するプロジェクト
        """
        self.selected_project = project
        
        # 選択中プロジェクト情報の更新
        if project:
            info_text = (
                f"プロジェクト名: {project['project_name']} | "
                f"担当者: {project['manager']} | "
                f"状態: {project['status']}"
            )
            self.selected_info.configure(text=info_text)
        else:
            self.selected_info.configure(text="プロジェクトが選択されていません")
            
        # プロジェクトカードの表示を更新
        self.refresh_projects()

    def show_document_processor(self):
        """ドキュメント処理ウィンドウを表示"""
        try:
            if not self.selected_project:
                messagebox.showwarning("警告", "プロジェクトを選択してください。")
                return

            # 設定の準備
            config = {
                'base_dir': str(Config.DATA_DIR),
                'db_path': str(Config.DB_PATH),
                'master_dir': str(Config.MASTER_DIR),
                'output_dir': str(Config.get_output_base_dir())
            }

            # DocumentProcessorManagerがない場合は初期化
            if not hasattr(self, 'doc_processor_manager'):
                self.doc_processor_manager = DocumentProcessorManager(config)

            # 既存のウィンドウがある場合はフォーカス
            if self.doc_processor_manager.is_window_open():
                self.doc_processor_manager.focus_window()
                return

            try:
                # 新しいウィンドウを作成
                processor_window = self.doc_processor_manager.create_window(
                    self.window,
                    self.selected_project
                )

                if processor_window:
                    # プロジェクトデータを設定
                    processor_window.set_project_data(self.selected_project)
                    logging.info("ドキュメント処理ウィンドウを表示しました")
                else:
                    raise ValueError("ウィンドウの作成に失敗しました")

            except Exception as e:
                logging.error(f"ドキュメント処理ウィンドウの作成エラー: {e}")
                raise

        except Exception as e:
            logging.error(f"ドキュメント処理ウィンドウの表示エラー: {str(e)}\n{traceback.format_exc()}")
            messagebox.showerror("エラー", "ドキュメント処理ウィンドウの表示に失敗しました。")

    def on_filter_change(self, choice):
        """
        フィルター選択時の処理
        
        Args:
            choice: 選択されたフィルター
        """
        self.current_filter = choice
        self.refresh_projects()

    def refresh_projects(self):
        """プロジェクト一覧の表示を更新"""
        if self.is_closing:
            logging.debug("ウィンドウが閉じているため更新をスキップ")
            return
        
        try:
            logging.debug("プロジェクト一覧の更新を開始")
            
            # 既存の内容をクリア
            for widget in self.projects_frame.winfo_children():
                widget.destroy()
            
            # プロジェクト一覧を取得とフィルタリング
            all_projects = self.db_manager.get_all_projects()
            selected_filter = self.filter_combo.get()
            self.project_list = [p for p in all_projects if selected_filter == '全て' or p['status'] == selected_filter]
            
            if not self.project_list:
                # プロジェクトが存在しない場合のメッセージ
                message = "該当するプロジェクトが存在しません。" if selected_filter == "進行中" else \
                         "プロジェクトが存在しません。"
                no_projects_label = ctk.CTkLabel(
                    self.projects_frame,
                    text=f"{message}\n新規プロジェクト作成ボタンからプロジェクトを作成してください。",
                    font=self.default_font,
                    text_color=self.colors.TEXT_SECONDARY
                )
                no_projects_label.pack(pady=20)
                logging.debug("プロジェクトが存在しないメッセージを表示")
                return
            
            # 各プロジェクトのカードを作成
            for project in self.project_list:
                self.create_project_card(project)
            
            logging.debug(f"{len(self.project_list)}件のプロジェクトを表示")
                
        except Exception as e:
            error_msg = f"プロジェクト一覧の更新エラー: {e}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            if not self.is_closing:
                messagebox.showerror("エラー", "プロジェクト一覧の更新に失敗しました。")

    def show_create_project_dialog(self):
        """新規プロジェクト作成ダイアログを表示"""
        if self.project_dialog is not None:
            self.project_dialog.window.destroy()
        
        self.project_dialog = QuickProjectForm(
            self.window,
            self.db_manager,
            callback=self.on_project_created
        )

    def edit_project(self, project_id: int):
        """
        プロジェクトの編集
        
        Args:
            project_id: 編集対象のプロジェクトID
        """
        try:
            project_data = self.db_manager.get_project(project_id)
            if not project_data:
                messagebox.showerror("エラー", "プロジェクトデータの取得に失敗しました。")
                return

            if self.project_dialog is not None:
                self.project_dialog.window.destroy()

            self.project_dialog = QuickProjectForm(
                self.window,
                self.db_manager,
                callback=self.on_project_updated,
                edit_mode=True,
                project_data=project_data
            )

        except Exception as e:
            logging.error(f"プロジェクト編集エラー: {e}")
            messagebox.showerror("エラー", "プロジェクトの編集に失敗しました。")

    def on_project_created(self):
        """プロジェクト作成後のコールバック"""
        self.refresh_projects()
            
        if self.project_dialog:
            self.project_dialog.window.destroy()
            self.project_dialog = None

    def on_project_updated(self):
        """プロジェクト更新後のコールバック"""
        self.refresh_projects()
            
        if self.project_dialog:
            self.project_dialog.window.destroy()
            self.project_dialog = None

    def delete_project(self, project_id: int):
        """
        プロジェクトの削除
        
        Args:
            project_id: 削除対象のプロジェクトID
        """
        if messagebox.askyesno("確認", "このプロジェクトを削除してもよろしいですか？"):
            try:
                self.db_manager.delete_project(project_id)
                # 削除したプロジェクトが選択中だった場合、選択を解除
                if self.selected_project and self.selected_project['project_id'] == project_id:
                    self.select_project(None)
                else:
                    self.refresh_projects()
                    
                messagebox.showinfo("成功", "プロジェクトを削除しました。")
            except Exception as e:
                logging.error(f"プロジェクト削除エラー: {e}")
                messagebox.showerror("エラー", "プロジェクトの削除に失敗しました。")

    def update_ganttchart_paths(self):
        """データベースの更新処理"""
        try:
            # 1. データベースマイグレーション
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            logging.info("データベースマイグレーションを開始します")
            
            # プロジェクトテーブルのマイグレーション
            self.db_manager._check_and_migrate_projects_table(cursor)
            
            # タスクテーブルのマイグレーション
            self.db_manager._migrate_tasks_table(cursor)
            
            conn.commit()
            conn.close()
            
            logging.info("データベースマイグレーションが完了しました")

            # 2. タスクデータの更新
            logging.info("タスクデータの更新を開始します")
            task_loader = TaskLoader(self.db_manager)
            task_loader.load_tasks()
            logging.info("タスクデータの更新が完了しました")

            # 3. ガントチャートパスの更新
            logging.info("ガントチャートパスの更新を開始します")
            updater = GanttChartUpdater(self.db_manager)
            stats = updater.update_ganttchart_paths()
            
            # 結果メッセージの作成
            message = (
                f"データベース更新が完了しました\n\n"
                f"1. データベースマイグレーション: 完了\n"
                f"2. タスクデータの更新: 完了\n"
                f"3. ガントチャート更新:\n"
                f"   - 処理対象プロジェクト数: {stats['total']}\n"
                f"   - 更新成功: {stats['updated']}\n"
                f"   - 未検出: {stats['not_found']}\n"
                f"   - エラー: {stats['error']}\n"
            )
            
            # 結果表示
            messagebox.showinfo("更新完了", message)
            
            # プロジェクト一覧を更新
            self.refresh_projects()
            
        except Exception as e:
            logging.error(f"データベース更新でエラー: {e}\n{traceback.format_exc()}")
            messagebox.showerror(
                "エラー",
                "データベースの更新中にエラーが発生しました。\n"
                "詳細はログを確認してください。"
            )

    def on_closing(self):
        """アプリケーション終了時の処理"""
        try:
            logging.debug("アプリケーション終了処理を開始")
            self.is_closing = True
            
            # ドキュメント処理マネージャーのクリーンアップ
            if self.doc_processor_manager:
                self.doc_processor_manager.cleanup()

            if self.project_dialog:
                try:
                    self.project_dialog.on_closing()
                except:
                    pass
                finally:
                    self.project_dialog = None

            if self.window:
                try:
                    # スケジューリングされたタスクをキャンセル
                    for after_id in self.window.tk.call('after', 'info'):
                        try:
                            self.window.after_cancel(after_id)
                        except:
                            continue

                    # ウィジェットの破棄
                    for widget in self.window.winfo_children():
                        try:
                            widget.destroy()
                        except:
                            continue

                    # メインウィンドウの破棄
                    self.window.quit()
                    self.window.destroy()
                except Exception as e:
                    logging.debug(f"ウィンドウ破棄時のエラー: {e}")
                finally:
                    self.window = None

            logging.debug("アプリケーション終了処理を完了")

        except Exception as e:
            logging.error(f"アプリケーション終了処理でエラーが発生: {e}")

    def launch_project_dashboard(self):
        """
        プロジェクト進捗ダッシュボードアプリを起動
        """
        try:
            import os
            import subprocess
            
            # 現在のプロジェクトを選択状態にする
            if not self.selected_project:
                messagebox.showinfo("情報", "プロジェクト進捗ダッシュボードを起動します。")
                
            # アプリケーションパス
            app_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            dashboard_path = os.path.join(app_path, "ProjectDashboard", "ProjectDashboard.exe")
            resolver_path = os.path.join(app_path, "path_resolver.py")
            
            # パス解決スクリプト実行
            if os.path.exists(resolver_path):
                subprocess.run(["python", resolver_path], check=True)
            
            # ダッシュボード起動
            if os.path.exists(dashboard_path):
                subprocess.Popen([dashboard_path], cwd=os.path.dirname(dashboard_path))
                logging.info("プロジェクト進捗ダッシュボードを起動しました")
            else:
                # パスが見つからない場合の処理
                messagebox.showwarning(
                    "警告", 
                    "プロジェクト進捗ダッシュボードが見つかりません。\n"
                    f"確認パス: {dashboard_path}"
                )
                
        except Exception as e:
            logging.error(f"ダッシュボード起動エラー: {e}")
            messagebox.showerror("エラー", f"プロジェクト進捗ダッシュボードの起動に失敗しました: {e}")

    def run(self):
        """アプリケーションの実行"""
        try:
            self.window.mainloop()
        except Exception as e:
            logging.error(f"メインループでエラーが発生: {e}")
            messagebox.showerror("エラー", "アプリケーションでエラーが発生しました。")