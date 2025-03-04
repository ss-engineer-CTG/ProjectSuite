# document_processor_factory.py

from pathlib import Path
from typing import Optional, Dict, Type
from CreateProjectList.processors.document_processor_base import DocumentProcessorBase
from CreateProjectList.processors.xlsx_processor import XLSXProcessor
from CreateProjectList.processors.xls_processor import XLSProcessor
from CreateProjectList.processors.doc_processor import DOCProcessor
from CreateProjectList.processors.docx_processor import DOCXProcessor
from CreateProjectList.utils.log_manager import LogManager

class DocumentProcessorFactory:
    """ドキュメントプロセッサーのファクトリークラス"""
    logger = LogManager().get_logger(__name__) 
    
    _processors = {
        '.xlsx': XLSXProcessor,
        '.xlsm': XLSXProcessor,  # xlsmファイルもXLSXProcessorで処理
        '.xls': XLSProcessor,
        '.doc': DOCProcessor,
        '.docx': DOCXProcessor
    }
    
    @classmethod
    def create_processor(cls, file_path: Path) -> Optional[DocumentProcessorBase]:
        """
        ファイルに適したプロセッサーのインスタンスを生成
        
        Args:
            file_path: 処理対象ファイルのパス
            
        Returns:
            Optional[DocumentProcessorBase]: プロセッサーのインスタンス。
                                          未対応の拡張子の場合はNone
        """
        processor_class = cls._processors.get(file_path.suffix.lower())
        if processor_class:
            cls.logger.info(f"Creating processor for file type: {file_path.suffix}")
            return processor_class()
        cls.logger.warning(f"No processor found for file type: {file_path.suffix}")
        return None
    
    @classmethod
    def get_supported_extensions(cls) -> list:
        """
        対応している拡張子の一覧を取得
        
        Returns:
            list: 対応拡張子のリスト
        """
        return list(cls._processors.keys())