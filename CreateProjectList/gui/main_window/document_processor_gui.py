"""ドキュメント処理GUIクラス"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from CreateProjectList.main.document_processor import DocumentProcessor
from CreateProjectList.utils.log_manager import LogManager
from CreateProjectList.utils.config_manager import ConfigManager
from CreateProjectList.gui.dialogs.settings_dialog import SettingsDialog
from CreateProjectList.gui.dialogs.progress_dialog import ProgressDialog

class DocumentProcessorGUI:
    """ドキュメント処理アプリケーションのGUIクラス"""
    
    def __init__(self, parent: tk.Widget):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
        """
        self.parent = parent
        self.logger = LogManager().get_logger(__name__)
        
        # プロセッサーの初期化
        self.processor = DocumentProcessor()
        
        # GUI要素
        self.input_folder_var = tk.StringVar(value="未設定")
        self.output_folder_var = tk.StringVar(value="未設定")
        self.project_info_var = tk.StringVar(value="プロジェクトが選択されていません")

        
        # スタイル設定
        self.setup_styles()
        
        # GUI初期化
        self.setup_gui()
        self.load_saved_settings()
        
        # データベース接続の初期化
        self.initialize_database_connection()
        
        # イベントバインド
        self.bind_events()
        
        self.logger.info("Document Processor GUI initialized")

    def load_saved_settings(self):
        """保存された設定を読み込む"""
        try:
            if self.processor.last_input_folder:
                path = self.processor.last_input_folder
                self.input_folder_var.set(path)
                self.logger.debug(f"Loaded input folder: {path}")

            if self.processor.last_output_folder:
                path = self.processor.last_output_folder
                self.output_folder_var.set(path)
                self.logger.debug(f"Loaded output folder: {path}")

            self.check_execution_ready()
            
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")

    def setup_styles(self):
        """カスタムスタイルの設定"""
        self.default_font = ("Meiryo", 12)
        self.header_font = ("Meiryo", 14, "bold")
        self.title_font = ("Meiryo", 20, "bold")
        
        # テーマ設定
        ctk.set_appearance_mode("dark")

    def setup_gui(self):
        """GUIの基本構造をセットアップ"""
        # メインフレーム
        self.main_frame = ctk.CTkFrame(self.parent)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ヘッダーフレーム
        header_frame = self._create_header_frame()
        
        # プロジェクト情報フレーム
        project_frame = self._create_project_frame()
        
        # フォルダ選択フレーム
        folder_frame = self._create_folder_frame()
        
        # 実行ボタン
        self.exec_button = self._create_execution_button()
        
        # ステータス表示
        self.status_var = tk.StringVar(value="準備完了")
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            textvariable=self.status_var,
            font=self.default_font
        )
        self.status_label.pack(pady=(10, 0))

    def _create_header_frame(self) -> ctk.CTkFrame:
        """ヘッダーフレームの作成"""
        header_frame = ctk.CTkFrame(self.main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # タイトル
        title_label = ctk.CTkLabel(
            header_frame,
            text="ドキュメント処理",
            font=self.title_font
        )
        title_label.pack(side="left", pady=10, padx=10)
        
        # 設定ボタン
        settings_button = ctk.CTkButton(
            header_frame,
            text="設定",
            command=self.open_settings,
            font=self.default_font,
            width=100
        )
        settings_button.pack(side="right", padx=10, pady=10)
        
        return header_frame

    def _create_project_frame(self) -> ctk.CTkFrame:
        """プロジェクト情報フレームの作成"""
        project_frame = ctk.CTkFrame(self.main_frame)
        project_frame.pack(fill="x", pady=(0, 20))
        
        # プロジェクト情報ラベル
        project_label = ctk.CTkLabel(
            project_frame,
            text="プロジェクト情報",
            font=self.header_font
        )
        project_label.pack(anchor="w", padx=10, pady=5)
        
        # プロジェクト詳細情報
        project_info = ctk.CTkLabel(
            project_frame,
            textvariable=self.project_info_var,
            font=self.default_font,
            wraplength=600
        )
        project_info.pack(anchor="w", padx=10, pady=5)
        
        return project_frame

    def _create_folder_frame(self) -> ctk.CTkFrame:
        """フォルダ選択フレームの作成"""
        folder_frame = ctk.CTkFrame(self.main_frame)
        folder_frame.pack(fill="x", pady=(0, 20))
        
        # 入力フォルダ選択
        input_frame = ctk.CTkFrame(folder_frame)
        input_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            input_frame,
            text="入力フォルダ:",
            font=self.default_font,
            width=120
        ).pack(side="left", padx=10)
        
        ctk.CTkLabel(
            input_frame,
            textvariable=self.input_folder_var,
            font=self.default_font
        ).pack(side="left", expand=True, fill="x", padx=10)
        
        ctk.CTkButton(
            input_frame,
            text="選択",
            command=self.select_input_folder,
            font=self.default_font,
            width=100
        ).pack(side="right", padx=10)
        
        # 出力フォルダ選択
        output_frame = ctk.CTkFrame(folder_frame)
        output_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            output_frame,
            text="出力フォルダ:",
            font=self.default_font,
            width=120
        ).pack(side="left", padx=10)
        
        ctk.CTkLabel(
            output_frame,
            textvariable=self.output_folder_var,
            font=self.default_font
        ).pack(side="left", expand=True, fill="x", padx=10)
        
        ctk.CTkButton(
            output_frame,
            text="選択",
            command=self.select_output_folder,
            font=self.default_font,
            width=100
        ).pack(side="right", padx=10)
        
        return folder_frame

    def _create_execution_button(self) -> ctk.CTkButton:
        """実行ボタンの作成"""
        button = ctk.CTkButton(
            self.main_frame,
            text="処理実行",
            command=self.execute_processing,
            font=self.title_font,
            width=200,
            height=50,
            state="disabled"
        )
        button.pack(pady=20)
        return button

    def initialize_database_connection(self):
        """データベース接続の初期化"""
        try:
            if self.processor.db_path:
                self.processor.db_context.get_connection()
                self.check_execution_ready()
                self.logger.info(f"Database connected: {self.processor.db_path}")
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            messagebox.showerror("エラー", "データベース接続エラー", parent=self.parent)

    def bind_events(self):
        """イベントのバインド"""
        # 設定変更イベント
        self.parent.bind("<<SettingsChanged>>", self.on_settings_changed)
        
        # ウィンドウ参照の取得
        window = self.parent.winfo_toplevel()
        
        # ウィンドウクローズイベント
        if isinstance(window, (tk.Tk, tk.Toplevel)):
            window.protocol("WM_DELETE_WINDOW", self.cleanup)

    def set_project_data(self, project_data: Dict[str, Any]):
        """
        プロジェクトデータの設定
        
        Args:
            project_data: プロジェクトデータ
        """
        try:
            self.processor.current_project_data = project_data
            self.update_project_info_display()
            self.check_execution_ready()
        except Exception as e:
            self.logger.error(f"プロジェクトデータ設定エラー: {e}")
            messagebox.showerror("エラー", "プロジェクトデータの設定に失敗しました", parent=self.parent)

    def update_project_info_display(self):
        """プロジェクト情報の表示を更新"""
        if self.processor.current_project_data:
            project = self.processor.current_project_data
            info_text = (
                f"プロジェクト名: {project['project_name']}\n"
                f"開始日: {project['start_date']}\n"
                f"担当者: {project['manager']}\n"
                f"工場: {project.get('factory', '未設定')}\n"
                f"工程: {project.get('process', '未設定')}\n"
                f"ライン: {project.get('line', '未設定')}"
            )
            self.project_info_var.set(info_text)
        else:
            self.project_info_var.set("プロジェクトが選択されていません")

    def select_input_folder(self):
        """入力フォルダの選択"""
        folder_path = filedialog.askdirectory(parent=self.parent)
        if folder_path:
            self.processor.last_input_folder = folder_path
            self.input_folder_var.set(folder_path)
            self.check_execution_ready()

    def select_output_folder(self):
        """出力フォルダの選択"""
        folder_path = filedialog.askdirectory(parent=self.parent)
        if folder_path:
            self.processor.last_output_folder = folder_path
            self.output_folder_var.set(folder_path)
            self.check_execution_ready()

    def check_execution_ready(self, event=None):
        """実行ボタンの有効/無効を設定"""
        try:
            if (self.processor.current_project_data and 
                self.processor.is_db_connected and
                self.processor.last_input_folder and 
                self.processor.last_output_folder and 
                Path(self.processor.last_input_folder).exists() and 
                Path(self.processor.last_output_folder).exists()):
                
                self.exec_button.configure(state="normal")
                self.status_var.set("実行可能")
            else:
                self.exec_button.configure(state="disabled")
                self.status_var.set("実行条件が満たされていません")
        except Exception as e:
            self.logger.error(f"実行可否チェックエラー: {e}")
            self.exec_button.configure(state="disabled")

    def execute_processing(self):
        """文書処理を実行"""
        try:
            # 確認ダイアログ表示
            if not messagebox.askyesno(
                "確認",
                f"以下のファイル処理を実行します。\n\n"
                f"入力フォルダ: {self.processor.last_input_folder}\n"
                f"出力フォルダ: {self.processor.last_output_folder}\n\n"
                "処理を開始しますか？",
                parent=self.parent
            ):
                return

            # 進捗ダイアログの作成
            progress_dialog = ProgressDialog(self.parent, "処理実行中")
            
            def process_func(*args, **kwargs):
                return self.processor.process_documents(
                    input_folder_path=self.processor.last_input_folder,
                    output_folder_path=self.processor.last_output_folder,
                    **kwargs
                )
            
            # コールバックの登録
            progress_dialog.add_event_handler('finished', self.on_processing_complete)
            
            # 処理の開始
            progress_dialog.start_process(process_func)
            
        except Exception as e:
            self.logger.error(f"処理実行エラー: {e}")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました: {str(e)}", parent=self.parent)

    def on_processing_complete(self, result):
        """
        処理完了時のコールバック
        
        Args:
            result: 処理結果
        """
        try:
            processed_count = len(result['processed'])
            error_count = len(result['errors'])
            
            message = f"処理が完了しました。\n\n"
            message += f"成功: {processed_count} ファイル\n"
            if error_count > 0:
                message += f"エラー: {error_count} ファイル\n\n"
                message += "エラーが発生したファイル:\n"
                for file_path, error in result['errors']:
                    message += f"- {file_path.name}: {error}\n"
            
            if error_count > 0:
                messagebox.showwarning("処理結果", message, parent=self.parent)
            else:
                messagebox.showinfo("処理結果", message, parent=self.parent)
                
        except Exception as e:
            self.logger.error(f"処理完了ハンドリングエラー: {e}")
            messagebox.showerror("エラー", "処理結果の表示に失敗しました", parent=self.parent)

    def open_settings(self):
        """設定ダイアログを開く"""
        try:
            SettingsDialog(self.parent, self.processor)
            self.logger.info("Settings dialog opened")
        except Exception as e:
            self.logger.error(f"設定ダイアログ表示エラー: {e}")
            messagebox.showerror("エラー", "設定ダイアログの表示に失敗しました", parent=self.parent)

    def on_settings_changed(self, event):
        """設定変更時の処理"""
        try:
            self.logger.info("Settings changed, reinitializing")
            self.initialize_database_connection()
            self.update_folder_display()
            self.check_execution_ready()
        except Exception as e:
            self.logger.error(f"設定変更反映エラー: {e}")
            messagebox.showerror("エラー", "設定の更新に失敗しました", parent=self.parent)

    def update_folder_display(self):
        """フォルダパスの表示を更新"""
        try:
            # 入力フォルダの表示更新
            if self.processor.last_input_folder:
                input_path = Path(self.processor.last_input_folder)
                if input_path.exists():
                    if input_path.is_dir():
                        # フォルダ内のファイルをチェック
                        if any(input_path.iterdir()):
                            self.input_folder_var.set(str(input_path))
                            self.input_status_var.set("準備完了")
                        else:
                            self.input_folder_var.set(str(input_path))
                            self.input_status_var.set("フォルダが空です")
                            self.show_warning("警告", "入力フォルダにファイルが存在しません")
                    else:
                        self.input_folder_var.set("未設定")
                        self.input_status_var.set("エラー")
                        self.show_error("エラー", "選択されたパスはフォルダではありません")
                else:
                    self.input_folder_var.set("未設定")
                    self.input_status_var.set("フォルダが存在しません")
                    self.show_warning("警告", "入力フォルダが存在しません")
            else:
                self.input_folder_var.set("未設定")
                self.input_status_var.set("フォルダ未選択")

            # 出力フォルダの表示更新
            if self.processor.last_output_folder:
                output_path = Path(self.processor.last_output_folder)
                if output_path.exists():
                    if output_path.is_dir():
                        # 出力フォルダが空かどうかチェック
                        if any(output_path.iterdir()):
                            self.output_folder_var.set(f"{str(output_path)} (空ではありません)")
                            self.output_status_var.set("警告")
                            self.show_warning("警告", "出力フォルダが空ではありません")
                        else:
                            self.output_folder_var.set(str(output_path))
                            self.output_status_var.set("準備完了")
                    else:
                        self.output_folder_var.set("未設定")
                        self.output_status_var.set("エラー")
                        self.show_error("エラー", "選択されたパスはフォルダではありません")
                else:
                    try:
                        # 出力フォルダの自動作成
                        output_path.mkdir(parents=True, exist_ok=True)
                        self.output_folder_var.set(str(output_path))
                        self.output_status_var.set("フォルダを作成しました")
                        self.logger.info(f"出力フォルダを作成: {output_path}")
                    except Exception as e:
                        self.output_folder_var.set("未設定")
                        self.output_status_var.set("エラー")
                        self.show_error("エラー", f"出力フォルダの作成に失敗しました: {e}")
            else:
                self.output_folder_var.set("未設定")
                self.output_status_var.set("フォルダ未選択")

            # 実行可能状態の更新
            self.check_execution_ready()

        except Exception as e:
            self.logger.error(f"フォルダ表示更新エラー: {e}")
            self.show_error("エラー", "フォルダ情報の更新に失敗しました")

    def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            # データベース接続のクローズ
            if self.processor.db_context:
                self.processor.db_context.close()
            
            # 一時ファイルの削除
            self.processor.cleanup_temp_files()
            
            self.logger.info("Resource cleanup completed")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
        finally:
            # 親ウィンドウに終了を通知
            if self.parent:
                self.parent.event_generate("<<DocumentProcessorClosed>>")

    def show_error(self, title: str, message: str):
        """
        エラーメッセージを表示
        
        Args:
            title: エラーダイアログのタイトル
            message: エラーメッセージ
        """
        messagebox.showerror(title, message, parent=self.parent)

    def show_warning(self, title: str, message: str):
        """
        警告メッセージを表示
        
        Args:
            title: 警告ダイアログのタイトル
            message: 警告メッセージ
        """
        messagebox.showwarning(title, message, parent=self.parent)

    def show_info(self, title: str, message: str):
        """
        情報メッセージを表示
        
        Args:
            title: 情報ダイアログのタイトル
            message: 情報メッセージ
        """
        messagebox.showinfo(title, message, parent=self.parent)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """
        はい/いいえの確認を表示
        
        Args:
            title: 確認ダイアログのタイトル
            message: 確認メッセージ
            
        Returns:
            bool: はいが選択された場合True
        """
        return messagebox.askyesno(title, message, parent=self.parent)