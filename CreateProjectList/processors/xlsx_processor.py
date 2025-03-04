# xlsx_processor.py

from pathlib import Path
from win32com import client
import pythoncom
import logging
import time
from typing import Dict, Optional, Callable
from CreateProjectList.processors.document_processor_base import DocumentProcessorBase
from CreateProjectList.utils.log_manager import LogManager

class XLSXProcessor(DocumentProcessorBase):
    """XLSX/XLSM形式のExcelファイル処理に特化したプロセッサー"""
    
    def __init__(self):
        """初期化"""
        super().__init__()
        self._excel_app = None
        self.logger = LogManager().get_logger(self.__class__.__name__)
    
    def can_process(self, file_path: Path) -> bool:
        """
        指定されたファイルが処理可能か判定
        
        Args:
            file_path: 処理対象ファイルのパス
            
        Returns:
            bool: xlsx/xlsmファイルの場合True
        """
        return file_path.suffix.lower() in ['.xlsx', '.xlsm']

    def process_file(self, input_path: Path, output_path: Path, replacements: Dict[str, str]) -> None:
        """
        Excelファイルを処理
        
        Args:
            input_path: 入力ファイルのパス
            output_path: 出力ファイルのパス
            replacements: 置換ルール辞書
        """
        excel = None
        workbook = None

        try:
            # COM初期化
            pythoncom.CoInitialize()
            
            self._report_progress(0, "Excelファイルを処理中...", str(input_path.name))

            # Excelアプリケーションの起動と設定
            excel = client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.ScreenUpdating = False
            
            self._report_progress(20, "ファイルを開いています...", str(input_path.name))
            
            # ブックを開く
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
                
                # シート内の処理実行
                self._process_cells(sheet, replacements)
                self._process_shapes(sheet.Shapes, replacements)

            # 保存処理
            self._report_progress(80, "ファイルを保存中...", str(output_path.name))
            
            # 出力先フォルダの作成
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True)
            self.logger.info(f"出力フォルダを作成: {output_path.parent}")
            
            # ファイル形式を判定して適切な形式で保存
            input_extension = input_path.suffix.lower()
            if input_extension == '.xlsm':
                # マクロ有効ブックとして保存 (xlOpenXMLWorkbookMacroEnabled)
                workbook.SaveAs(
                    str(output_path.resolve()),
                    FileFormat=52
                )
                self.logger.info("マクロ有効ブックとして保存")
            else:
                # 通常のxlsxとして保存 (xlOpenXMLWorkbook)
                workbook.SaveAs(
                    str(output_path.resolve()),
                    FileFormat=51
                )
                self.logger.info("標準ブックとして保存")
            
            self._report_progress(100, "処理完了", f"{input_path.name} -> {output_path.name}")
            self.logger.info(f"ファイル処理完了: {input_path} -> {output_path}")

        except Exception as e:
            self.logger.error(f"Excel処理エラー - {input_path}: {str(e)}")
            raise
        
        finally:
            # クリーンアップ
            try:
                if workbook:
                    workbook.Close(SaveChanges=False)
                if excel:
                    excel.Quit()
            except Exception as e:
                self.logger.warning(f"Excel終了処理でエラー: {str(e)}")
            finally:
                pythoncom.CoUninitialize()

    def _process_cells(self, worksheet, replacements: Dict[str, str]) -> None:
        """
        ワークシート内のセルを処理
        
        Args:
            worksheet: 処理対象ワークシート
            replacements: 置換ルール辞書
        """
        try:
            for old_text, new_text in replacements.items():
                if self._should_cancel():
                    return
                    
                # セル内の文字列を検索
                found_cell = worksheet.Cells.Find(
                    What=old_text,
                    LookAt=2,       # xlPart: 部分一致
                    MatchCase=True   # 大文字小文字を区別
                )
                
                if found_cell is not None:
                    first_address = found_cell.Address
                    
                    while True:
                        original_text = str(found_cell.Value)
                        # 基底クラスの_process_textを使用して置換処理を実行
                        new_value = self._process_text(original_text, {old_text: new_text})
                        if original_text != new_value:
                            found_cell.Value = new_value
                        
                        found_cell = worksheet.Cells.FindNext(found_cell)
                        # 検索が一周して最初のセルに戻ったら終了
                        if found_cell is None or found_cell.Address == first_address:
                            break

        except Exception as e:
            self.logger.error(f"セル処理エラー - {worksheet.Name}: {str(e)}")
            raise

    def _process_shapes(self, shapes, replacements: Dict[str, str]) -> None:
        """
        Shape内のテキストを処理
        
        Args:
            shapes: 処理対象のShapesコレクション
            replacements: 置換ルール辞書
        """
        for shape in shapes:
            if self._should_cancel():
                return
                
            try:
                # TextFrame2が利用可能な場合はそちらを優先
                if hasattr(shape, 'TextFrame2'):
                    if shape.TextFrame2.HasText:
                        text_range = shape.TextFrame2.TextRange
                        original_text = text_range.Text
                        new_text = self._process_text(original_text, replacements)
                        if original_text != new_text:
                            text_range.Text = new_text
                
                # 従来のTextFrameを使用
                elif hasattr(shape, 'TextFrame'):
                    if shape.TextFrame.HasText:
                        text_range = shape.TextFrame.Characters
                        original_text = text_range.Text
                        new_text = self._process_text(original_text, replacements)
                        if original_text != new_text:
                            text_range.Text = new_text
                            
            except Exception as e:
                shape_name = getattr(shape, 'Name', 'unknown')
                self.logger.warning(f"Shape '{shape_name}' の処理でエラー: {str(e)}")