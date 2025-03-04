"""統合機能のエラーハンドリング"""

import logging
import traceback
from typing import Optional, Callable, Dict, Any
import tkinter as tk
from tkinter import messagebox
from CreateProjectList.utils.log_manager import LogManager

class IntegrationError(Exception):
    """統合機能の基本エラークラス"""
    pass

class ConfigurationError(IntegrationError):
    """設定関連のエラー"""
    pass

class WindowError(IntegrationError):
    """ウィンドウ管理のエラー"""
    pass

class ResourceError(IntegrationError):
    """リソース管理のエラー"""
    pass

class IntegrationErrorHandler:
    """統合機能のエラーハンドリングクラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = LogManager().get_logger(__name__)
        self._error_registry = self._setup_error_registry()

    def _setup_error_registry(self) -> Dict[type, Callable]:
        """
        エラータイプごとのハンドラー登録
        
        Returns:
            Dict[type, Callable]: エラータイプとハンドラーの対応辞書
        """
        return {
            ConfigurationError: self._handle_configuration_error,
            WindowError: self._handle_window_error,
            ResourceError: self._handle_resource_error,
            Exception: self._handle_general_error
        }

    def handle_error(self, 
                    error: Exception, 
                    window: Optional[tk.Toplevel] = None,
                    cleanup_func: Optional[Callable] = None) -> None:
        """
        エラーの処理
        
        Args:
            error: 発生したエラー
            window: エラーダイアログの親ウィンドウ（オプション）
            cleanup_func: クリーンアップ関数（オプション）
        """
        try:
            # エラータイプに応じたハンドラーの取得
            handler = self._get_error_handler(type(error))
            
            # クリーンアップ処理の実行
            if cleanup_func:
                try:
                    cleanup_func()
                except Exception as cleanup_error:
                    self.logger.error(f"クリーンアップエラー: {cleanup_error}")
            
            # エラー処理の実行
            handler(error, window)
            
        except Exception as e:
            self.logger.error(f"エラーハンドリング中の例外: {e}\n{traceback.format_exc()}")
            self._show_error_dialog(
                "致命的なエラー",
                f"エラー処理中に問題が発生しました:\n{str(e)}",
                window
            )

    def _get_error_handler(self, error_type: type) -> Callable:
        """
        エラータイプに応じたハンドラーを取得
        
        Args:
            error_type: エラーの型
            
        Returns:
            Callable: エラーハンドラー関数
        """
        for error_class, handler in self._error_registry.items():
            if issubclass(error_type, error_class):
                return handler
        return self._handle_general_error

    def _handle_configuration_error(self, error: ConfigurationError, window: Optional[tk.Toplevel]) -> None:
        """
        設定エラーの処理
        
        Args:
            error: 設定エラー
            window: 親ウィンドウ
        """
        self.logger.error(f"設定エラー: {error}\n{traceback.format_exc()}")
        self._show_error_dialog(
            "設定エラー",
            f"設定の読み込みまたは検証中にエラーが発生しました:\n{str(error)}",
            window
        )

    def _handle_window_error(self, error: WindowError, window: Optional[tk.Toplevel]) -> None:
        """
        ウィンドウ関連エラーの処理
        
        Args:
            error: ウィンドウエラー
            window: 親ウィンドウ
        """
        self.logger.error(f"ウィンドウエラー: {error}\n{traceback.format_exc()}")
        self._show_error_dialog(
            "ウィンドウエラー",
            f"ウィンドウの操作中にエラーが発生しました:\n{str(error)}",
            window
        )

    def _handle_resource_error(self, error: ResourceError, window: Optional[tk.Toplevel]) -> None:
        """
        リソースエラーの処理
        
        Args:
            error: リソースエラー
            window: 親ウィンドウ
        """
        self.logger.error(f"リソースエラー: {error}\n{traceback.format_exc()}")
        self._show_error_dialog(
            "リソースエラー",
            f"リソースの管理中にエラーが発生しました:\n{str(error)}",
            window
        )

    def _handle_general_error(self, error: Exception, window: Optional[tk.Toplevel]) -> None:
        """
        一般エラーの処理
        
        Args:
            error: 一般エラー
            window: 親ウィンドウ
        """
        self.logger.error(f"一般エラー: {error}\n{traceback.format_exc()}")
        self._show_error_dialog(
            "エラー",
            f"予期せぬエラーが発生しました:\n{str(error)}",
            window
        )

    def _show_error_dialog(self, title: str, message: str, parent: Optional[tk.Toplevel] = None) -> None:
        """
        エラーダイアログの表示
        
        Args:
            title: ダイアログのタイトル
            message: エラーメッセージ
            parent: 親ウィンドウ
        """
        try:
            messagebox.showerror(title, message, parent=parent)
        except Exception as e:
            self.logger.error(f"エラーダイアログ表示エラー: {e}")