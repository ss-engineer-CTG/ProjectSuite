# gui/__init__.py

"""
GUIコンポーネントパッケージ
"""

# メインウィンドウ
from .main_window import (
    DocumentProcessorGUI,
    ExecutionFrame,
    DatabaseFrame,
    ProjectFrame
)

# ダイアログ
from .dialogs import (
    BaseDialog,
    DatabaseViewer,
    ProgressDialog,
    RuleDialog,
    SettingsDialog
)

# 共通コンポーネント
from .components import (
    AccordionFrame,
    ScrolledFrame
)

__all__ = [
    # メインウィンドウ
    'DocumentProcessorGUI',
    'ExecutionFrame',
    'DatabaseFrame',
    'ProjectFrame',
    
    # ダイアログ
    'BaseDialog',
    'DatabaseViewer',
    'ProgressDialog',
    'RuleDialog',
    'SettingsDialog',
    
    # 共通コンポーネント
    'AccordionFrame',
    'ScrolledFrame'
]