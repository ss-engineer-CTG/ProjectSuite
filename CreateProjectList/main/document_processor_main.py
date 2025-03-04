# document_processor_main.py

import tkinter as tk
import logging
import sys
import traceback
from pathlib import Path
from CreateProjectList.gui.main_window import DocumentProcessorGUI
from CreateProjectList.main.document_processor import DocumentProcessor
from CreateProjectList.utils.log_manager import LogManager

def process_with_project_id(project_id: int) -> bool:
    """
    指定されたプロジェクトIDに対してドキュメント処理を実行
    
    Args:
        project_id: 処理対象のプロジェクトID
    Returns:
        bool: 処理成功時True
    """
    processor = DocumentProcessor()
    
    try:
        processor.connect_database()
        project_data = processor.fetch_project_data(project_id)
        
        if not processor.last_input_folder or not processor.last_output_folder:
            raise ValueError("入力フォルダまたは出力フォルダが設定されていません。")
            
        def progress_callback(progress: float, status: str, detail: str):
            """進捗コールバック"""
            logging.info(f"Progress: {progress}%, Status: {status}, Detail: {detail}")
        
        def cancel_check() -> bool:
            """キャンセルチェック"""
            return False
            
        result = processor.process_documents(
            processor.last_input_folder,
            processor.last_output_folder,
            progress_callback=progress_callback,
            cancel_check=cancel_check
        )
        
        logging.info(f"プロジェクト {project_id} の処理が完了しました")
        logging.info(f"処理成功: {len(result['processed'])} ファイル")
        if result.get('cancelled', False):
            logging.info("処理はキャンセルされました")
            
        if result['errors']:
            logging.warning(f"処理エラー: {len(result['errors'])} ファイル")
            for file_path, error in result['errors']:
                logging.error(f"  {file_path}: {error}")
        
        return True
        
    except Exception as e:
        logging.error(f"処理エラー: {e}\n{traceback.format_exc()}")
        raise
    finally:
        processor.close_database()

def main():
    """メイン実行関数"""
    try:
        # ログマネージャーの初期化
        LogManager()

        if len(sys.argv) > 1:
            try:
                project_id = int(sys.argv[1])
                logging.info(f"コマンドラインモード: プロジェクト {project_id} の処理を開始します")
                process_with_project_id(project_id)
                logging.info(f"プロジェクト {project_id} の処理が完了しました")
                return
            except ValueError:
                error_msg = "プロジェクトIDは数値で指定してください"
                logging.error(error_msg)
                print(f"エラー: {error_msg}")
                sys.exit(1)
            except Exception as e:
                logging.error(f"処理エラー: {e}\n{traceback.format_exc()}")
                print(f"エラー: {str(e)}")
                sys.exit(1)
        else:
            logging.info("GUIモードでアプリケーションを起動します")
            root = tk.Tk()
            root.title("ドキュメント処理アプリケーション")
            app = DocumentProcessorGUI(root)
            root.mainloop()

    except Exception as e:
        logging.error(f"アプリケーション実行エラー: {e}\n{traceback.format_exc()}")
        print(f"エラー: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()