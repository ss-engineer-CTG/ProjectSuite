"""
パス設定ダイアログ - パスレジストリの診断と設定用UI
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path
import logging
import webbrowser
from datetime import datetime

# パスレジストリをインポート
try:
    # まずSystemPathで試す
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, str(Path(sys._MEIPASS).parent))
    else:
        # 開発環境では相対パスを探索
        current_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(current_dir))
    
    from PathRegistry import PathRegistry
except ImportError as e:
    # フォールバックとして相対的な検索
    import importlib.util
    
    # パスレジストリを検索して動的にインポート
    registry_paths = [
        Path(__file__).parent.parent.parent.parent / "PathRegistry.py",
        Path(__file__).parent.parent.parent / "PathRegistry.py",
        Path(__file__).parent.parent / "PathRegistry.py"
    ]
    
    for path in registry_paths:
        if path.exists():
            spec = importlib.util.spec_from_file_location("PathRegistry", path)
            PathRegistry_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(PathRegistry_module)
            PathRegistry = PathRegistry_module.PathRegistry
            break
    else:
        # インポートできない場合はダミーのPathRegistryを定義
        class PathRegistry:
            @classmethod
            def get_instance(cls):
                return cls()
                
            def get_path(self, key, default=None):
                return default
                
            def get_all_paths(self):
                return {}
                
            def diagnose(self):
                return {"issues": []}
                
            def auto_repair(self, issues=None):
                return {"repaired": [], "failed": []}
                
            def register_path(self, key, path):
                pass
                
            def export_config(self, path=None):
                return False
                
            def create_report(self, format="text"):
                return ""

# ロガー
logger = logging.getLogger(__name__)

def create_path_config_dialog(parent, registry=None):
    """
    パス設定ダイアログを作成
    
    Args:
        parent: 親ウィンドウ
        registry: PathRegistryインスタンス（Noneの場合は自動取得）
        
    Returns:
        tk.Toplevel: ダイアログウィンドウ
    """
    if registry is None:
        registry = PathRegistry.get_instance()
    
    # ダイアログの作成
    dialog = tk.Toplevel(parent)
    dialog.title("パス設定")
    dialog.geometry("800x600")
    dialog.transient(parent)
    dialog.grab_set()
    
    # スタイル設定
    style = ttk.Style()
    style.configure("TButton", padding=6)
    style.configure("Warning.TLabel", foreground="orange")
    style.configure("Error.TLabel", foreground="red")
    style.configure("Success.TLabel", foreground="green")
    style.configure("Info.TLabel", foreground="blue")
    
    # メインフレーム
    frame = ttk.Frame(dialog, padding=10)
    frame.pack(fill="both", expand=True)
    
    # 現在の診断結果
    diagnosis = registry.diagnose()
    
    # タブコントロール
    notebook = ttk.Notebook(frame)
    notebook.pack(fill="both", expand=True, pady=10)
    
    # 設定タブ
    settings_tab = ttk.Frame(notebook, padding=10)
    notebook.add(settings_tab, text="パス設定")
    
    # 診断タブ
    diagnostics_tab = ttk.Frame(notebook, padding=10)
    issue_count = len(diagnosis["issues"])
    color = "red" if issue_count > 0 else "black"
    notebook.add(diagnostics_tab, text=f"診断結果 ({issue_count}件の問題)")
    
    # 設定タブの内容 - ScrollableFrame
    settings_canvas = tk.Canvas(settings_tab)
    scrollbar = ttk.Scrollbar(settings_tab, orient="vertical", command=settings_canvas.yview)
    scrollable_frame = ttk.Frame(settings_canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: settings_canvas.configure(
            scrollregion=settings_canvas.bbox("all")
        )
    )
    
    settings_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    settings_canvas.configure(yscrollcommand=scrollbar.set)
    
    settings_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # パス入力フィールド
    entries = {}
    
    # グループ分け
    groups = {}
    for key in registry.get_all_paths().keys():
        prefix = key.split('_')[0] if '_' in key else 'OTHER'
        if prefix not in groups:
            groups[prefix] = []
        groups[prefix].append(key)
    
    row = 0
    
    # グループごとに表示
    for group_name, keys in sorted(groups.items()):
        # グループヘッダー
        ttk.Label(scrollable_frame, text=f"{group_name}", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=(10, 5))
        row += 1
        
        # グループ内のパス
        for key in sorted(keys):
            path = registry.get_path(key)
            path_obj = Path(path) if path else None
            
            # キーラベル
            ttk.Label(scrollable_frame, text=key).grid(
                row=row, column=0, sticky="w", padx=(20, 5))
            
            # パス入力フィールド
            entry = ttk.Entry(scrollable_frame, width=50)
            entry.insert(0, path if path else "")
            entry.grid(row=row, column=1, sticky="ew", padx=5)
            entries[key] = entry
            
            # 状態表示
            if path_obj and path_obj.exists():
                ttk.Label(scrollable_frame, text="OK", style="Success.TLabel").grid(
                    row=row, column=2, padx=5)
            elif path:
                ttk.Label(scrollable_frame, text="未検出", style="Error.TLabel").grid(
                    row=row, column=2, padx=5)
            
            # 参照ボタン
            def browse_callback(k=key, e=entry):
                browse_path(k, e, registry, dialog)
            
            ttk.Button(scrollable_frame, text="参照", command=browse_callback).grid(
                row=row, column=3, padx=5)
            
            row += 1
    
    # 診断タブの内容
    if diagnosis["issues"]:
        # 問題リスト
        issues_frame = ttk.Frame(diagnostics_tab)
        issues_frame.pack(fill="both", expand=True)
        
        # スクロール可能なリスト
        scrollbar = ttk.Scrollbar(issues_frame)
        scrollbar.pack(side="right", fill="y")
        
        issue_list = tk.Listbox(issues_frame, height=10, width=80, font=("Arial", 9))
        issue_list.pack(side="left", fill="both", expand=True)
        
        issue_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=issue_list.yview)
        
        # 問題の表示
        for i, issue in enumerate(diagnosis["issues"]):
            severity = "⚠️" if issue["severity"] == "high" else "ℹ️"
            issue_list.insert("end", f"{severity} {issue['key']}: {issue['type']}")
        
        # 詳細表示
        detail_frame = ttk.LabelFrame(diagnostics_tab, text="詳細", padding=10)
        detail_frame.pack(fill="both", expand=True, pady=10)
        
        detail_text = tk.Text(detail_frame, height=10, wrap="word")
        detail_text.pack(fill="both", expand=True)
        
        # 選択時の詳細表示
        def show_issue_details(event):
            selection = issue_list.curselection()
            if selection:
                issue = diagnosis["issues"][selection[0]]
                detail_text.delete(1.0, "end")
                detail_text.insert("end", f"キー: {issue['key']}\n")
                detail_text.insert("end", f"パス: {issue['path']}\n")
                detail_text.insert("end", f"問題: {issue['type']}\n")
                detail_text.insert("end", f"重要度: {issue['severity']}\n\n")
                detail_text.insert("end", f"解決策:\n{issue['solution']}")
        
        issue_list.bind("<<ListboxSelect>>", show_issue_details)
        
        # 自動修復ボタン
        def auto_repair_and_refresh():
            """自動修復を実行して結果を表示"""
            result = registry.auto_repair(diagnosis["issues"])
            repaired_count = len(result['repaired'])
            failed_count = len(result['failed'])
            
            message = f"修復完了\n\n成功: {repaired_count}件\n失敗: {failed_count}件"
            
            if failed_count > 0:
                message += "\n\n失敗した項目:"
                for item in result['failed']:
                    message += f"\n- {item['key']}: {item['reason']}"
            
            messagebox.showinfo("修復結果", message, parent=dialog)
            
            # ダイアログを再構築
            dialog.destroy()
            create_path_config_dialog(parent, registry)
        
        ttk.Button(diagnostics_tab, text="自動修復を試みる", 
                 command=auto_repair_and_refresh).pack(pady=10)
    else:
        ttk.Label(diagnostics_tab, text="問題は見つかりませんでした", style="Success.TLabel").pack(pady=20)
    
    # ボタンフレーム
    button_frame = ttk.Frame(frame)
    button_frame.pack(fill="x", pady=10)
    
    # 保存関数
    def save_paths():
        """パス設定を保存"""
        try:
            # 入力された値を検証して登録
            for key, entry in entries.items():
                new_path = entry.get().strip()
                if new_path:  # 空でなければ登録
                    registry.register_path(key, new_path)
            
            # 設定ファイルに保存
            if registry.export_config():
                messagebox.showinfo("保存完了", "パス設定を保存しました", parent=dialog)
                dialog.destroy()
            else:
                messagebox.showerror("保存エラー", "設定ファイルの保存に失敗しました", parent=dialog)
        except Exception as e:
            messagebox.showerror("エラー", f"パス設定の保存に失敗しました:\n{str(e)}", parent=dialog)
    
    # レポート出力関数
    def export_report():
        """レポートを出力"""
        try:
            # 保存先を選択
            file_path = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML", "*.html"), ("JSON", "*.json"), ("テキスト", "*.txt")],
                initialdir=os.path.expanduser("~"),
                title="レポートの保存先を選択",
                parent=dialog
            )
            
            if not file_path:
                return
                
            # 拡張子に応じて形式を決定
            ext = Path(file_path).suffix.lower()
            if ext == '.html':
                format = "html"
            elif ext == '.json':
                format = "json"
            else:
                format = "text"
            
            # レポートを生成して保存
            report = registry.create_report(format=format)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report)
            
            # ブラウザで開く（HTMLの場合）
            if ext == '.html':
                webbrowser.open(file_path)
            
            messagebox.showinfo("レポート出力", f"レポートを保存しました:\n{file_path}", parent=dialog)
            
        except Exception as e:
            messagebox.showerror("エラー", f"レポート出力に失敗しました:\n{str(e)}", parent=dialog)
    
    # 保存ボタン
    ttk.Button(button_frame, text="保存", command=save_paths).pack(side="right", padx=5)
    
    # キャンセルボタン
    ttk.Button(button_frame, text="キャンセル", command=dialog.destroy).pack(side="right", padx=5)
    
    # レポートボタン
    ttk.Button(button_frame, text="レポート出力", command=export_report).pack(side="left", padx=5)
    
    # 診断実行ボタン
    def refresh_diagnosis():
        """診断を再実行して結果を更新"""
        dialog.destroy()
        create_path_config_dialog(parent, registry)
    
    ttk.Button(button_frame, text="診断実行", command=refresh_diagnosis).pack(side="left", padx=5)
    
    # ダイアログを親の中央に配置
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    
    return dialog

def browse_path(key, entry, registry, dialog):
    """
    パス参照ダイアログを表示
    
    Args:
        key: パスキー
        entry: 対応する入力フィールド
        registry: PathRegistryインスタンス
        dialog: 親ダイアログ
    """
    try:
        # 現在のパス
        current_path = entry.get()
        initial_dir = os.path.dirname(current_path) if current_path else os.path.expanduser("~")
        
        # ディレクトリ/ファイル選択
        if key.endswith('_DIR'):
            # ディレクトリ選択
            path = filedialog.askdirectory(
                initialdir=initial_dir,
                title=f"{key}の選択",
                parent=dialog
            )
        elif key.endswith(('_FILE', '_PATH')):
            # ファイル選択
            path = filedialog.askopenfilename(
                initialdir=initial_dir,
                title=f"{key}の選択",
                parent=dialog
            )
        else:
            # どちらかわからない場合
            path = filedialog.askdirectory(
                initialdir=initial_dir,
                title=f"{key}の選択",
                parent=dialog
            )
            if not path:  # ディレクトリが選択されなかった場合はファイル選択
                path = filedialog.askopenfilename(
                    initialdir=initial_dir,
                    title=f"{key}の選択",
                    parent=dialog
                )
        
        if path:
            # エントリに設定
            entry.delete(0, tk.END)
            entry.insert(0, path)
            
    except Exception as e:
        messagebox.showerror("エラー", f"パス選択に失敗しました:\n{str(e)}", parent=dialog)

# テスト用
if __name__ == "__main__":
    root = tk.Tk()
    root.title("パス設定テスト")
    root.geometry("200x100")
    
    registry = PathRegistry.get_instance()
    
    def open_dialog():
        create_path_config_dialog(root, registry)
    
    ttk.Button(root, text="設定を開く", command=open_dialog).pack(pady=20)
    
    root.mainloop()