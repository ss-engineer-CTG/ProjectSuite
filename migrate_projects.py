# migrate_projects.py
import os
import shutil
import sqlite3
from pathlib import Path
import logging
import tkinter as tk
from tkinter import filedialog, messagebox

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("migration.log"),
            logging.StreamHandler()
        ]
    )

def get_paths_from_gui():
    """GUIから移行元、移行先、DBパスを取得"""
    root = tk.Tk()
    root.withdraw()  # GUIを非表示にする
    
    # デフォルトパスの準備
    docs_dir = Path.home() / "Documents" / "ProjectSuite"
    default_src = docs_dir / "ProjectManager" / "data" / "projects"
    default_dst = Path.home() / "Desktop" / "projects"
    default_db = docs_dir / "ProjectManager" / "data" / "projects.db"
    
    # 移行元の選択
    messagebox.showinfo("プロジェクト移行", "移行元のプロジェクトフォルダを選択してください")
    src_dir = filedialog.askdirectory(initialdir=default_src)
    if not src_dir:
        messagebox.showinfo("キャンセル", "移行元フォルダの選択がキャンセルされました")
        return None, None, None
    
    # 移行先の選択
    messagebox.showinfo("プロジェクト移行", "移行先のプロジェクトフォルダを選択してください")
    dst_dir = filedialog.askdirectory(initialdir=default_dst)
    if not dst_dir:
        messagebox.showinfo("キャンセル", "移行先フォルダの選択がキャンセルされました")
        return None, None, None
    
    # データベースの選択
    messagebox.showinfo("プロジェクト移行", "データベースファイル(projects.db)を選択してください")
    db_path = filedialog.askopenfilename(
        initialdir=default_db.parent, 
        title="データベースファイルを選択",
        filetypes=[("Database files", "*.db"), ("All files", "*.*")]
    )
    if not db_path:
        messagebox.showinfo("キャンセル", "データベースファイルの選択がキャンセルされました")
        return None, None, None
    
    return src_dir, dst_dir, db_path

def migrate_projects(src_dir, dst_dir, db_path):
    """
    プロジェクトを移行し、データベースを更新
    
    Args:
        src_dir: 移行元ディレクトリ
        dst_dir: 移行先ディレクトリ
        db_path: データベースファイルのパス
    """
    conn = None
    try:
        # 移行先ディレクトリの作成
        Path(dst_dir).mkdir(parents=True, exist_ok=True)
        
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # プロジェクトパスの取得
        cursor.execute("SELECT project_id, project_name, project_path FROM projects")
        projects = cursor.fetchall()
        
        migrated = 0
        failed = 0
        skipped = 0
        
        logging.info(f"{len(projects)}件のプロジェクトを移行します")
        
        for project_id, project_name, project_path in projects:
            if not project_path:
                logging.warning(f"プロジェクト {project_name} (ID: {project_id}) にパスが設定されていません")
                skipped += 1
                continue
                
            # 元のパスが存在するか確認
            project_path_obj = Path(project_path)
            if not project_path_obj.exists():
                logging.warning(f"プロジェクト {project_name} (ID: {project_id}) のパスが存在しません: {project_path}")
                skipped += 1
                continue
            
            # フォルダ名の取得
            folder_name = project_path_obj.name
            new_path = Path(dst_dir) / folder_name
            
            # フォルダのコピー
            try:
                if new_path.exists():
                    logging.warning(f"移行先に既に同名フォルダが存在します: {new_path}")
                    skipped += 1
                    continue
                    
                shutil.copytree(project_path, new_path)
                logging.info(f"プロジェクト {project_name} を移行: {project_path} -> {new_path}")
                
                # データベースの更新
                cursor.execute(
                    "UPDATE projects SET project_path = ? WHERE project_id = ?",
                    (str(new_path), project_id)
                )
                
                migrated += 1
                
            except Exception as e:
                logging.error(f"プロジェクト {project_name} の移行中にエラー: {e}")
                failed += 1
        
        # 変更を確定
        conn.commit()
        logging.info("データベースの更新が完了しました")
        
        return {
            "total": len(projects),
            "migrated": migrated,
            "failed": failed,
            "skipped": skipped
        }
        
    except Exception as e:
        logging.error(f"データベース操作エラー: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def main():
    """メイン処理"""
    try:
        setup_logging()
        
        # GUIからパスを取得
        src_dir, dst_dir, db_path = get_paths_from_gui()
        if not all([src_dir, dst_dir, db_path]):
            return
        
        # 確認ダイアログ
        result = messagebox.askyesno(
            "確認", 
            f"以下の情報で移行を開始します。よろしいですか？\n\n"
            f"移行元: {src_dir}\n"
            f"移行先: {dst_dir}\n"
            f"DB パス: {db_path}"
        )
        
        if result:
            logging.info("移行を開始します")
            stats = migrate_projects(src_dir, dst_dir, db_path)
            
            # 結果の表示
            messagebox.showinfo(
                "移行完了",
                f"プロジェクトの移行が完了しました\n\n"
                f"対象プロジェクト: {stats['total']}件\n"
                f"移行成功: {stats['migrated']}件\n"
                f"スキップ: {stats['skipped']}件\n"
                f"エラー: {stats['failed']}件\n\n"
                f"詳細はmigration.logを確認してください。"
            )
            
            logging.info(f"移行が完了しました: {stats}")
        else:
            logging.info("移行がキャンセルされました")
            
    except Exception as e:
        logging.error(f"移行処理エラー: {e}")
        messagebox.showerror("エラー", f"移行処理中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()