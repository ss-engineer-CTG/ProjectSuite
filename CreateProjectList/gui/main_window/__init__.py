# gui/main_window/__init__.py

from .document_processor_gui import DocumentProcessorGUI
from .execution_frame import ExecutionFrame
from .database_frame import DatabaseFrame
from .project_frame import ProjectFrame

__all__ = [
    'DocumentProcessorGUI',
    'ExecutionFrame',
    'DatabaseFrame',
    'ProjectFrame'
]