"""プロジェクトフォームの基本クラス"""

import customtkinter as ctk
from datetime import datetime
import logging
from typing import Optional, Dict, Any, Callable

from ProjectManager.src.core.config import Config
from ProjectManager.src.ui.styles.color_scheme import ColorScheme

class BaseProjectForm:
    """プロジェクトフォームの基本クラス"""
    
    def __init__(self):
        self.colors = ColorScheme
        self.default_font = ("Meiryo", 12)
        self.header_font = ("Meiryo", 14, "bold")
        self.fields = {}  # 入力フィールドの参照を保持
        
    def _create_section_label(self, parent, text: str):
        """セクションラベルの作成"""
        frame = ctk.CTkFrame(
            parent,
            fg_color=self.colors.CARD_BG
        )
        frame.pack(fill="x", padx=20, pady=(20, 10))
        
        label = ctk.CTkLabel(
            frame,
            text=text,
            font=self.header_font,
            text_color=self.colors.TEXT_PRIMARY,
            anchor="w"
        )
        label.pack(pady=10, padx=10, anchor="w")
        
        return frame

    def _create_input_field(self, parent, label_text, required=False, attr_name=None, 
                         placeholder=None, validator=None):
        """入力フィールドの作成"""
        frame = ctk.CTkFrame(
            parent,
            fg_color=self.colors.CARD_BG,
            border_color=self.colors.FRAME_BORDER,
            border_width=1
        )
        frame.pack(fill="x", padx=20, pady=5)
        
        # ラベル
        label = ctk.CTkLabel(
            frame,
            text=f"{label_text}{'*' if required else ''}",
            anchor="w",
            width=120,
            font=self.default_font,
            text_color=self.colors.TEXT_PRIMARY
        )
        label.pack(side="left", padx=(10, 5))
        
        # 入力フィールド
        entry = ctk.CTkEntry(
            frame,
            width=400,
            placeholder_text=placeholder,
            font=self.default_font,
            fg_color=self.colors.INPUT_BG,
            text_color=self.colors.INPUT_TEXT,
            border_color=self.colors.INPUT_BORDER
        )
        entry.pack(side="left", padx=5, expand=True, fill="x")
        
        if attr_name:
            setattr(self, attr_name, entry)
            self.fields[attr_name] = entry
            
        return entry, frame

    def _create_combo_field(self, parent, label_text, attr_name, values, required=False, command=None):
        """コンボボックスフィールドの作成"""
        frame = ctk.CTkFrame(
            parent,
            fg_color=self.colors.CARD_BG,
            border_color=self.colors.FRAME_BORDER,
            border_width=1
        )
        frame.pack(fill="x", padx=20, pady=5)
        
        # ラベル
        label = ctk.CTkLabel(
            frame,
            text=f"{label_text}{'*' if required else ''}",
            anchor="w",
            width=120,
            font=self.default_font,
            text_color=self.colors.TEXT_PRIMARY
        )
        label.pack(side="left", padx=(10, 5))
        
        # コンボボックス
        combo = ctk.CTkComboBox(
            frame,
            width=400,
            values=values,
            state="readonly",
            command=command,
            font=self.default_font,
            fg_color=self.colors.INPUT_BG,
            text_color=self.colors.INPUT_TEXT,
            border_color=self.colors.INPUT_BORDER,
            button_color=self.colors.BUTTON_PRIMARY
        )
        combo.pack(side="left", padx=5, expand=True, fill="x")
        
        if attr_name:
            setattr(self, attr_name, combo)
            self.fields[attr_name] = combo
            
        return combo

    def _validate_date(self, value):
        """日付のバリデーション"""
        try:
            datetime.strptime(value, '%Y-%m-%d')
            return True, ""
        except ValueError:
            return False, "日付の形式が正しくありません (YYYY-MM-DD)"

    def _validate_project_name(self, value):
        """プロジェクト名のバリデーション"""
        if len(value) < 3:
            return False, "プロジェクト名は3文字以上で入力してください"
        return True, ""

    def load_default_values(self):
        """デフォルト値の読み込み"""
        try:
            # ConfigManagerを直接使用して設定を取得
            from ProjectManager.src.core.config_manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # デフォルト値を取得
            default_values = {}
            if config and 'defaults' in config:
                default_values = {
                    'project_name': config['defaults'].get('project_name', ''),
                    'manager': config['defaults'].get('manager', ''),
                    'reviewer': config['defaults'].get('reviewer', ''),
                    'approver': config['defaults'].get('approver', ''),
                    'division': config['defaults'].get('division', ''),
                    'factory': config['defaults'].get('factory', ''),
                    'process': config['defaults'].get('process', ''),
                    'line': config['defaults'].get('line', '')
                }
                
                # ウィジェットに値を設定
                for field_name, value in default_values.items():
                    if field_name in self.fields and value:
                        widget = self.fields[field_name]
                        if isinstance(widget, ctk.CTkEntry):
                            widget.delete(0, 'end')
                            widget.insert(0, value)
                        elif isinstance(widget, ctk.CTkComboBox):
                            widget.set(value)
                        
        except Exception as e:
            logging.warning(f"デフォルト値の読み込みエラー: {e}")