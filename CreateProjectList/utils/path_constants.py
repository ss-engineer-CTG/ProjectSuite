"""パス関連の定数定義"""

from enum import Enum, auto

class PathKeys:
    """パスのキー定数"""
    
    # 基本パス
    ROOT = "ROOT"
    USER_DATA_DIR = "USER_DATA_DIR"
    DATA_DIR = "DATA_DIR"
    
    # 出力/プロジェクトパス (OUTPUT_BASE_DIRを主として使用)
    OUTPUT_BASE_DIR = "OUTPUT_BASE_DIR"
    PROJECTS_DIR = "PROJECTS_DIR"  # OUTPUT_BASE_DIRのエイリアス
    
    # CreateProjectList関連パス
    CPL_DIR = "CPL_DIR"
    CPL_CONFIG_DIR = "CPL_CONFIG_DIR" 
    CPL_CONFIG_PATH = "CPL_CONFIG_PATH"
    CPL_TEMP_DIR = "CPL_TEMP_DIR"
    CPL_TEMPLATES_DIR = "CPL_TEMPLATES_DIR"
    CPL_CACHE_DIR = "CPL_CACHE_DIR"
    CPL_INPUT_FOLDER = "CPL_INPUT_FOLDER"
    CPL_OUTPUT_FOLDER = "CPL_OUTPUT_FOLDER"
    
    # ProjectManager関連パス
    PM_DATA_DIR = "PM_DATA_DIR"
    PM_MASTER_DIR = "PM_MASTER_DIR"
    PM_DB_PATH = "PM_DB_PATH"
    PM_TEMPLATES_DIR = "PM_TEMPLATES_DIR"
    PM_OUTPUT_BASE_DIR = "PM_OUTPUT_BASE_DIR"
    
    # 後方互換性のためのエイリアス
    DB_PATH = "DB_PATH"
    TEMPLATES_DIR = "TEMPLATES_DIR" 
    
    # 共通パス
    LOGS_DIR = "LOGS_DIR"
    TEMP_DIR = "TEMP_DIR"
    BACKUP_DIR = "BACKUP_DIR"
    EXPORTS_DIR = "EXPORTS_DIR"

class PathType(Enum):
    """パスタイプの列挙型"""
    
    ROOT = auto()         # ルートディレクトリ
    CONFIG = auto()       # 設定ディレクトリ
    DATA = auto()         # データディレクトリ
    OUTPUT = auto()       # 出力ディレクトリ
    TEMPLATE = auto()     # テンプレートディレクトリ
    TEMP = auto()         # 一時ディレクトリ
    LOG = auto()          # ログディレクトリ
    MASTER = auto()       # マスターデータディレクトリ
    EXPORT = auto()       # エクスポートディレクトリ
    DATABASE = auto()     # データベースファイル
    UNKNOWN = auto()      # 不明なパスタイプ

def get_path_type(key: str) -> PathType:
    """
    パスキーからパスタイプを取得
    
    Args:
        key: パスキー
        
    Returns:
        PathType: パスタイプ
    """
    key = key.upper()
    
    if key in ["ROOT"]:
        return PathType.ROOT
    elif "CONFIG" in key:
        return PathType.CONFIG
    elif key in ["DATA_DIR", "PM_DATA_DIR"]:
        return PathType.DATA
    elif key in ["OUTPUT_BASE_DIR", "PROJECTS_DIR", "PM_OUTPUT_BASE_DIR", "CPL_OUTPUT_FOLDER"]:
        return PathType.OUTPUT
    elif key in ["TEMPLATES_DIR", "PM_TEMPLATES_DIR", "CPL_TEMPLATES_DIR", "CPL_INPUT_FOLDER"]:
        return PathType.TEMPLATE
    elif "TEMP" in key:
        return PathType.TEMP
    elif "LOG" in key:
        return PathType.LOG
    elif "MASTER" in key:
        return PathType.MASTER
    elif "EXPORT" in key:
        return PathType.EXPORT
    elif "DB" in key or "DATABASE" in key:
        return PathType.DATABASE
    else:
        return PathType.UNKNOWN