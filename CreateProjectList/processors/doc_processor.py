from pathlib import Path
from win32com import client
import pythoncom
from docx import Document
from typing import Dict
from CreateProjectList.processors.document_processor_base import DocumentProcessorBase
from CreateProjectList.utils.log_manager import LogManager

class DOCProcessor(DocumentProcessorBase):
    """DOC形式のWordファイル処理に特化したプロセッサー"""
    def __init__(self):
        """初期化"""
        self.logger = LogManager().get_logger(self.__class__.__name__)
    
    def can_process(self, file_path: Path) -> bool:
        """
        指定されたファイルが処理可能か判定
        
        Args:
            file_path: 処理対象ファイルのパス
            
        Returns:
            bool: docファイルの場合True
        """
        return file_path.suffix.lower() == '.doc'

    def process_file(self, input_path: Path, output_path: Path, replacements: Dict[str, str]) -> None:
        """
        DOCファイルを処理
        
        Args:
            input_path: 入力ファイルのパス
            output_path: 出力ファイルのパス
            replacements: 置換ルール辞書
        """
        word = None
        document = None

        try:
            pythoncom.CoInitialize()
            
            self._report_progress(0, "DOCファイルを処理中...", str(input_path.name))

            # Wordアプリケーションの起動
            word = client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False
            
            self._report_progress(20, "ファイルを開いています...", str(input_path.name))
            
            # ファイルを開く
            document = word.Documents.Open(str(input_path.resolve()))
            
            # 本文処理
            self._report_progress(40, "本文を処理中...", "")
            self._process_content(document, replacements)
            
            # 図形処理
            self._report_progress(60, "図形を処理中...", "")
            self._process_shapes(document, replacements)
            
            # ヘッダー/フッター処理
            self._report_progress(80, "ヘッダー/フッターを処理中...", "")
            for section in document.Sections:
                self._process_headers_footers(section, replacements)
            
            # DOC形式で保存
            document.SaveAs(str(output_path.resolve()), FileFormat=0)  # 0 = doc形式
            
            self._report_progress(100, "処理完了", f"{input_path.name} -> {output_path.name}")

        except Exception as e:
            self.logger.error(f"DOC処理エラー - {input_path}: {str(e)}")
            raise
        
        finally:
            if document:
                document.Close(SaveChanges=False)
            if word:
                word.Quit()
            pythoncom.CoUninitialize()

    def _process_content(self, document, replacements: Dict[str, str]) -> None:
        """
        本文テキストおよびテーブルセルのテキストを処理（DOC用）

        Args:
            document: 処理対象ドキュメント
            replacements: 置換ルール辞書
        """
        try:
            # テキストの置換処理
            for old_text, new_text in replacements.items():
                # 検索と置換のオプションを設定
                find = document.Content.Find
                find.ClearFormatting()
                find.Replacement.ClearFormatting()
                
                # 「なし」「未設定」の場合は空文字に置換
                replacement_text = "" if new_text in ["なし", "未設定"] else new_text
                
                # 置換実行
                find.Execute(
                    FindText=old_text,
                    ReplaceWith=replacement_text,
                    Replace=2,  # 2は全て置換
                    Forward=True,
                    Wrap=1,     # 1は文書全体
                    Format=False,
                    MatchCase=False,
                    MatchWholeWord=False,
                    MatchWildcards=False,
                    MatchSoundsLike=False,
                    MatchAllWordForms=False
                )

        except Exception as e:
            self.logger.error(f"本文処理エラー: {str(e)}")
            raise

    def _process_shapes(self, document, replacements: Dict[str, str]) -> None:
        """
        図形内のテキストを処理（DOC用）
        
        Args:
            document: 処理対象ドキュメント
            replacements: 置換ルール辞書
        """
        # 通常の図形の処理
        for shape in document.Shapes:
            try:
                # テキストフレームを持つ図形かチェック
                if shape.TextFrame.HasText:
                    text_range = shape.TextFrame.TextRange
                    # 置換処理
                    for old_text, new_text in replacements.items():
                        # 検索と置換のオプションを設定
                        find = text_range.Find
                        find.ClearFormatting()
                        find.Replacement.ClearFormatting()
                        
                        # 「なし」「未設定」の場合は空文字に置換
                        replacement_text = "" if new_text in ["なし", "未設定"] else new_text
                        
                        # 置換実行
                        find.Execute(
                            FindText=old_text,
                            ReplaceWith=replacement_text,
                            Replace=2,  # 2は全て置換
                            Forward=True,
                            Wrap=1,     # 1は文書全体
                            Format=False,
                            MatchCase=False,
                            MatchWholeWord=False,
                            MatchWildcards=False,
                            MatchSoundsLike=False,
                            MatchAllWordForms=False
                        )
            except Exception as e:
                shape_name = getattr(shape, 'Name', 'unknown')
                self.logger.warning(f"DOC Shape '{shape_name}' の処理でエラー: {str(e)}")
                continue

        # InlineShapes（インライン図形）の処理
        for shape in document.InlineShapes:
            try:
                if hasattr(shape, 'TextFrame') and shape.TextFrame.HasText:
                    text_range = shape.TextFrame.TextRange
                    # 置換処理
                    for old_text, new_text in replacements.items():
                        find = text_range.Find
                        find.ClearFormatting()
                        find.Replacement.ClearFormatting()
                        
                        # 「なし」「未設定」の場合は空文字に置換
                        replacement_text = "" if new_text in ["なし", "未設定"] else new_text
                        
                        # 置換実行
                        find.Execute(
                            FindText=old_text,
                            ReplaceWith=replacement_text,
                            Replace=2,
                            Forward=True,
                            Wrap=1,
                            Format=False,
                            MatchCase=False,
                            MatchWholeWord=False,
                            MatchWildcards=False,
                            MatchSoundsLike=False,
                            MatchAllWordForms=False
                        )
            except Exception as e:
                shape_name = getattr(shape, 'Name', 'unknown')
                self.logger.warning(f"DOC インライン図形 '{shape_name}' の処理でエラー: {str(e)}")
                continue

    def _process_headers_footers(self, section, replacements: Dict[str, str]) -> None:
        """
        ヘッダーとフッターのテキストを処理

        Args:
            section: 処理対象のセクション
            replacements: 置換ルール辞書
        """
        try:
            # ヘッダーの処理
            for header_type in range(1, 4):  # wdHeaderFooterPrimary=1, wdHeaderFooterFirstPage=2, wdHeaderFooterEvenPages=3
                try:
                    header = section.Headers(header_type)
                    if header.Exists:
                        for old_text, new_text in replacements.items():
                            find = header.Range.Find
                            find.ClearFormatting()
                            find.Replacement.ClearFormatting()
                            
                            # 「なし」「未設定」の場合は空文字に置換
                            replacement_text = "" if new_text in ["なし", "未設定"] else new_text
                            
                            # 置換実行
                            find.Execute(
                                FindText=old_text,
                                ReplaceWith=replacement_text,
                                Replace=2,
                                Forward=True,
                                Wrap=1,
                                Format=False,
                                MatchCase=False,
                                MatchWholeWord=False,
                                MatchWildcards=False,
                                MatchSoundsLike=False,
                                MatchAllWordForms=False
                            )
                except Exception as e:
                    self.logger.warning(f"ヘッダー処理エラー (type={header_type}): {str(e)}")
                    continue

            # フッターの処理
            for footer_type in range(1, 4):
                try:
                    footer = section.Footers(footer_type)
                    if footer.Exists:
                        for old_text, new_text in replacements.items():
                            find = footer.Range.Find
                            find.ClearFormatting()
                            find.Replacement.ClearFormatting()
                            
                            # 「なし」「未設定」の場合は空文字に置換
                            replacement_text = "" if new_text in ["なし", "未設定"] else new_text
                            
                            # 置換実行
                            find.Execute(
                                FindText=old_text,
                                ReplaceWith=replacement_text,
                                Replace=2,
                                Forward=True,
                                Wrap=1,
                                Format=False,
                                MatchCase=False,
                                MatchWholeWord=False,
                                MatchWildcards=False,
                                MatchSoundsLike=False,
                                MatchAllWordForms=False
                            )
                except Exception as e:
                    self.logger.warning(f"フッター処理エラー (type={footer_type}): {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"ヘッダー/フッター処理エラー: {str(e)}")
            raise