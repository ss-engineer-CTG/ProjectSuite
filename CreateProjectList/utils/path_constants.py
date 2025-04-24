"""
パス定義の定数モジュール
アプリケーション全体で使用するパスキーの定義
"""
from enum import Enum

class PathKeys:
    """パスレジストリで使用するキー定数"""
    
    # 基本パス
    ROOT = "ROOT"
    USER_DATA_DIR = "USER_DATA_DIR"
    
    # CreateProjectList関連
    CPL_DIR = "CPL_DIR"
    CPL_CONFIG_DIR = "CPL_CONFIG_DIR"
    CPL_CONFIG_PATH = "CPL_CONFIG_PATH"
    CPL_TEMP_DIR = "CPL_TEMP_DIR"
    CPL_TEMPLATES_DIR = "CPL_TEMPLATES_DIR"
    CPL_CACHE_DIR = "CPL_CACHE_DIR"
    CPL_INPUT_FOLDER = "CPL_INPUT_FOLDER"
    CPL_OUTPUT_FOLDER = "CPL_OUTPUT_FOLDER"
    
    # ProjectManager関連
    PM_DATA_DIR = "PM_DATA_DIR"
    PM_DB_PATH = "DB_PATH"
    PM_MASTER_DIR = "MASTER_DIR"
    PM_TEMPLATES_DIR = "TEMPLATES_DIR"
    PM_PROJECTS_DIR = "PROJECTS_DIR"
    PM_EXPORTS_DIR = "EXPORTS_DIR"
    
    # 共通
    LOGS_DIR = "LOGS_DIR"
    TEMP_DIR = "TEMP_DIR"
    BACKUP_DIR = "BACKUP_DIR"