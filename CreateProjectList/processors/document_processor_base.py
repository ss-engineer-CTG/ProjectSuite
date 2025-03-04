# CreateProjectList_base.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Callable
from CreateProjectList.utils.log_manager import LogManager

class DocumentProcessorBase(ABC):
    """文書処理の基底クラス"""
    
    def __init__(self):
        self.logger = LogManager().get_logger(self.__class__.__name__)
        self._progress_callback = None
        self._cancel_check = None
    
    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        """
        指定されたファイルを処理可能か判定
        
        Args:
            file_path: 処理対象ファイルのパス
            
        Returns:
            bool: 処理可能な場合はTrue
        """
        pass
    
    @abstractmethod
    def process_file(self, input_path: Path, output_path: Path, replacements: Dict[str, str]) -> None:
        """
        ファイルを処理
        
        Args:
            input_path: 入力ファイルのパス
            output_path: 出力ファイルのパス
            replacements: 置換ルール辞書
        """
        pass
    
    def set_progress_callback(self, callback: Optional[Callable[[float, str, str], None]]) -> None:
        """進捗コールバックを設定"""
        self._progress_callback = callback
    
    def set_cancel_check(self, callback: Optional[Callable[[], bool]]) -> None:
        """キャンセルチェックコールバックを設定"""
        self._cancel_check = callback
    
    def _report_progress(self, progress: float, status: str, detail: str = "") -> None:
        """進捗を報告"""
        if self._progress_callback:
            self._progress_callback(progress, status, detail)
    
    def _should_cancel(self) -> bool:
        """処理をキャンセルすべきか確認"""
        return bool(self._cancel_check and self._cancel_check())

    def _process_text(self, text: str, replacements: Dict[str, str]) -> str:
        """
        文字列置換処理
        
        Args:
            text: 置換対象テキスト
            replacements: 置換ルール辞書
            
        Returns:
            str: 置換後のテキスト
        """
        if not isinstance(text, str):
            return text
            
        result = text
        for old_text, new_text in replacements.items():
            # 「なし」と「None」の場合は空文字列に置換
            if str(new_text).lower() in ['なし', 'none']:
                result = result.replace(old_text, '')
            else:
                result = result.replace(old_text, str(new_text))
        
        return result