# processors/__init__.py

from .document_processor_base import DocumentProcessorBase
from .document_processor_factory import DocumentProcessorFactory
from .xlsx_processor import XLSXProcessor
from .xls_processor import XLSProcessor
from .doc_processor import DOCProcessor
from .docx_processor import DOCXProcessor
from .folder_processor import FolderProcessor

__all__ = [
    'DocumentProcessorBase',
    'DocumentProcessorFactory',
    'XLSXProcessor',
    'XLSProcessor',
    'DOCProcessor',
    'DOCXProcessor',
    'FolderProcessor'
]