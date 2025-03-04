# xls_processor.py

from pathlib import Path
from win32com import client
import pythoncom
import logging
from typing import Dict
from CreateProjectList.processors.document_processor_base import DocumentProcessorBase
from CreateProjectList.utils.log_manager import LogManager

class XLSProcessor(DocumentProcessorBase):
    """XLS形式のExcelファイル処理に特化したプロセッサー"""
    def __init__(self):
        """初期化"""
        super().__init__()
        self.logger = LogManager().get_logger(self.__class__.__name__)
    
    def can_process(self, file_path: Path) -> bool:
        """
        指定されたファイルが処理可能か判定
        
        Args:
            file_path: 処理対象ファイルのパス
            
        Returns:
            bool: xlsファイルの場合True
        """
        return file_path.suffix.lower() == '.xls'

    def process_file(self, input_path: Path, output_path: Path, replacements: Dict[str, str]) -> None:
        """
        XLSファイルを処理
        
        Args:
            input_path: 入力ファイルのパス
            output_path: 出力ファイルのパス
            replacements: 置換ルール辞書
        """
        excel = None
        workbook = None

        try:
            pythoncom.CoInitialize()
            
            self._report_progress(0, "XLSファイルを処理中...", str(input_path.name))

            # Excelアプリケーションの起動（XLS用の設定）
            excel = client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            self._report_progress(20, "ファイルを開いています...", str(input_path.name))
            
            # 互換モードでファイルを開く
            workbook = excel.Workbooks.Open(str(input_path.resolve()))
            
            # シート処理
            sheet_count = len(workbook.Worksheets)
            for i, sheet in enumerate(workbook.Worksheets, 1):
                if self._should_cancel():
                    return
                
                progress = 20 + (i / sheet_count * 60)
                self._report_progress(
                    progress,
                    f"シート処理中 ({i}/{sheet_count})",
                    sheet.Name
                )
                
                self._process_cells(sheet, replacements)
                self._process_shapes(sheet, replacements)

            # 保存処理
            self._report_progress(80, "ファイルを保存中...", str(output_path.name))
            
            # XLS形式で保存
            workbook.SaveAs(str(output_path.resolve()), FileFormat=56)  # 56 = xls形式
            
            self._report_progress(100, "処理完了", f"{input_path.name} -> {output_path.name}")

        except Exception as e:
            self.logger.error(f"XLS処理エラー - {input_path}: {str(e)}")
            raise
        
        finally:
            if workbook:
                workbook.Close(SaveChanges=False)
            if excel:
                excel.Quit()
            pythoncom.CoUninitialize()

    def _process_cells(self, worksheet, replacements: Dict[str, str]) -> None:
        """
        最適化されたセル処理（XLS用）
        
        Args:
            worksheet: 処理対象ワークシート
            replacements: 置換ルール辞書
        """
        try:
            for old_text, new_text in replacements.items():
                # FindメソッドでXLSファイル内を検索
                found_cell = worksheet.Cells.Find(
                    What=old_text,
                    LookAt=2,  # 部分一致
                    SearchOrder=1,  # 行方向
                    MatchCase=True
                )
                
                if found_cell is not None:
                    first_address = found_cell.Address
                    while True:
                        original_text = str(found_cell.Text)
                        # _process_textを使用して置換処理を実行
                        new_value = self._process_text(original_text, {old_text: new_text})
                        if original_text != new_value:
                            found_cell.Value = new_value
                            
                        found_cell = worksheet.Cells.FindNext(found_cell)
                        if found_cell is None or found_cell.Address == first_address:
                            break

        except Exception as e:
            self.logger.error(f"XLSセル処理エラー: {str(e)}")

    def _process_shapes(self, sheet, replacements: Dict[str, str]) -> None:
        """
        Shape内のテキストを処理（XLS用）
        
        Args:
            sheet: 処理対象シート
            replacements: 置換ルール辞書
        """
        for shape in sheet.Shapes:
            try:
                if hasattr(shape, 'TextFrame') and shape.TextFrame.HasText:
                    text_range = shape.TextFrame.Characters
                    original_text = text_range.Text
                    new_text = self._process_text(original_text, replacements)
                    if original_text != new_text:
                        text_range.Text = new_text
                        
            except Exception as e:
                shape_name = getattr(shape, 'Name', 'unknown')
                self.logger.warning(f"XLS Shape '{shape_name}' の処理でエラー: {str(e)}")