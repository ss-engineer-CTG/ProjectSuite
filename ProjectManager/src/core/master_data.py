import pandas as pd
from pathlib import Path
import logging
from typing import List, Dict, Optional, TypedDict
from datetime import datetime

class MasterDataEntry(TypedDict):
    code: str
    name: str

class MasterDataManager:
    def __init__(self, master_file_path: Path):
        """
        マスタデータ管理クラスの初期化
        
        Args:
            master_file_path (Path): マスタデータCSVファイルのパス
        """
        self.master_file_path = master_file_path
        self.master_data: Optional[pd.DataFrame] = None
        self.last_updated: Optional[datetime] = None
        self.load_master_data()
    
    def load_master_data(self) -> None:
        """
        マスタデータをCSVファイルから読み込む
        
        Raises:
            ValueError: データの読み込みまたは検証に失敗した場合
        """
        last_error = None
        for encoding in ['utf-8', 'utf-8-sig', 'cp932']:
            try:
                self.master_data = pd.read_csv(
                    self.master_file_path,
                    encoding=encoding,
                    dtype=str  # 全てのカラムを文字列として読み込み
                )
                self._validate_master_data()
                self.last_updated = datetime.now()
                logging.info(f"マスタデータを {encoding} で正常に読み込みました")
                return
            except UnicodeDecodeError:
                continue
            except Exception as e:
                last_error = e
                logging.error(f"{encoding} でのマスタデータ読み込みでエラー: {e}")
        
        error_msg = f"マスタデータの読み込みに失敗しました: {last_error}" if last_error else "マスタデータを読み込めませんでした"
        raise ValueError(error_msg)
            
    def _validate_master_data(self) -> None:
        """
        マスタデータの妥当性検証
        
        Raises:
            ValueError: 必要なカラムが存在しない場合
        """
        required_columns = [
            'division_code', 'division_name',
            'factory_code', 'factory_name',
            'process_code', 'process_name',
            'line_code', 'line_name'
        ]
        
        missing_columns = [col for col in required_columns 
                          if col not in self.master_data.columns]
                          
        if missing_columns:
            raise ValueError(f"必要なカラムがありません: {', '.join(missing_columns)}")

    def get_divisions(self) -> List[MasterDataEntry]:
        """
        事業部の一覧を取得
        
        Returns:
            List[MasterDataEntry]: 事業部情報のリスト
        """
        if self.master_data is None:
            return []
        
        divisions = self.master_data[['division_code', 'division_name']].drop_duplicates()
        return [
            {'code': row['division_code'], 'name': row['division_name']}
            for _, row in divisions.iterrows()
        ]
    
    def get_factories(self, division_code: Optional[str] = None) -> List[MasterDataEntry]:
        """
        工場の一覧を取得
        
        Args:
            division_code: フィルタリングする事業部コード（Noneの場合は全て取得）
            
        Returns:
            List[MasterDataEntry]: 工場情報のリスト
        """
        if self.master_data is None:
            return []
        
        factories = self.master_data[['division_code', 'factory_code', 'factory_name']]
        if division_code is not None:  # Noneの場合はフィルタリングしない
            factories = factories[factories['division_code'] == division_code]
        
        factories = factories[['factory_code', 'factory_name']].drop_duplicates()
        return [
            {'code': row['factory_code'], 'name': row['factory_name']}
            for _, row in factories.iterrows()
        ]
    
    def get_processes(self, division_code: Optional[str] = None,
                     factory_code: Optional[str] = None) -> List[MasterDataEntry]:
        """
        工程の一覧を取得
        
        Args:
            division_code: フィルタリングする事業部コード（Noneの場合は全て取得）
            factory_code: フィルタリングする工場コード（Noneの場合は全て取得）
            
        Returns:
            List[MasterDataEntry]: 工程情報のリスト
        """
        if self.master_data is None:
            return []
        
        processes = self.master_data[
            ['division_code', 'factory_code', 'process_code', 'process_name']
        ]
        
        filters = []
        if division_code is not None:
            filters.append(processes['division_code'] == division_code)
        if factory_code is not None:
            filters.append(processes['factory_code'] == factory_code)
            
        if filters:
            processes = processes[pd.concat(filters, axis=1).all(axis=1)]
        
        processes = processes[['process_code', 'process_name']].drop_duplicates()
        return [
            {'code': row['process_code'], 'name': row['process_name']}
            for _, row in processes.iterrows()
        ]
    
    def get_lines(self, division_code: Optional[str] = None,
                 factory_code: Optional[str] = None,
                 process_code: Optional[str] = None) -> List[MasterDataEntry]:
        """
        ラインの一覧を取得
        
        Args:
            division_code: フィルタリングする事業部コード（Noneの場合は全て取得）
            factory_code: フィルタリングする工場コード（Noneの場合は全て取得）
            process_code: フィルタリングする工程コード（Noneの場合は全て取得）
            
        Returns:
            List[MasterDataEntry]: ライン情報のリスト
        """
        if self.master_data is None:
            return []
        
        lines = self.master_data[
            ['division_code', 'factory_code', 'process_code', 'line_code', 'line_name']
        ]
        
        filters = []
        if division_code is not None:
            filters.append(lines['division_code'] == division_code)
        if factory_code is not None:
            filters.append(lines['factory_code'] == factory_code)
        if process_code is not None:
            filters.append(lines['process_code'] == process_code)
            
        if filters:
            lines = lines[pd.concat(filters, axis=1).all(axis=1)]
        
        lines = lines[['line_code', 'line_name']].drop_duplicates()
        return [
            {'code': row['line_code'], 'name': row['line_name']}
            for _, row in lines.iterrows()
        ]
    
    def validate_combination(self, division_code: str, factory_code: str,
                           process_code: str, line_code: str) -> bool:
        """
        選択された組み合わせが有効かチェック
        
        Args:
            division_code: 事業部コード
            factory_code: 工場コード
            process_code: 工程コード
            line_code: ラインコード
            
        Returns:
            bool: 組み合わせが有効な場合True
        """
        if self.master_data is None:
            return False
        
        filtered = self.master_data[
            (self.master_data['division_code'] == division_code) &
            (self.master_data['factory_code'] == factory_code) &
            (self.master_data['process_code'] == process_code) &
            (self.master_data['line_code'] == line_code)
        ]
        
        return len(filtered) > 0
    
    def get_name_by_code(self, code: str, type_name: str) -> Optional[str]:
        """
        コードに対応する名前を取得
        
        Args:
            code: 検索するコード
            type_name: 検索する項目タイプ (division/factory/process/line)
            
        Returns:
            Optional[str]: 対応する名前。見つからない場合はNone
        """
        if self.master_data is None:
            return None
        
        code_col = f"{type_name}_code"
        name_col = f"{type_name}_name"
        
        if code_col not in self.master_data.columns or name_col not in self.master_data.columns:
            return None
        
        filtered = self.master_data[self.master_data[code_col] == code]
        if len(filtered) > 0:
            return filtered.iloc[0][name_col]
        
        return None

    def reload_master_data(self) -> None:
        """マスタデータの再読み込み"""
        self.load_master_data()