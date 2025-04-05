"""設定解決用ユーティリティ"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from CreateProjectList.utils.log_manager import LogManager

class ConfigResolver:
    """設定解決用ユーティリティクラス"""
    
    logger = LogManager().get_logger(__name__)
    
    @staticmethod
    def resolve_integration_paths(main_config: dict) -> Dict[str, str]:
        """
        統合機能用のパス解決
        
        Args:
            main_config: メインアプリケーションの設定
            
        Returns:
            Dict[str, str]: 解決されたパス情報
            
        Raises:
            ValueError: パス解決に失敗した場合
        """
        try:
            # ユーザードキュメントフォルダを優先
            user_docs_dir = Path.home() / "Documents" / "ProjectSuite"
            
            # 環境変数でのオーバーライドを確認
            if "PMSUITE_DATA_DIR" in os.environ:
                user_docs_dir = Path(os.environ["PMSUITE_DATA_DIR"])
            
            # main_configのデータディレクトリを確認
            if main_config.get('data_dir'):
                data_dir = Path(main_config['data_dir'])
                if data_dir.is_absolute():
                    # 絶対パスの場合はそれを使用
                    if data_dir.exists() or data_dir.parent.exists():
                        user_docs_dir = data_dir
            
            # ベースディレクトリの解決
            base_dir = Path(main_config.get('base_dir', ''))
            if not base_dir.is_absolute():
                base_dir = Path(os.getcwd()) / base_dir
            
            # 各種パスの解決
            paths = {
                'template_dir': str(user_docs_dir / 'templates'),
                'output_dir': str(user_docs_dir / 'projects'),
                'temp_dir': str(user_docs_dir / 'temp'),
                'master_dir': str(user_docs_dir / 'master'),
                'export_dir': str(user_docs_dir / 'exports')
            }
            
            # パスの正規化
            paths = {key: os.path.normpath(path) for key, path in paths.items()}
            
            ConfigResolver.logger.info(f"パス解決完了: {paths}")
            return paths
            
        except Exception as e:
            ConfigResolver.logger.error(f"パス解決エラー: {e}")
            raise ValueError(f"パス解決に失敗しました: {e}")

    @staticmethod
    def validate_paths(paths: Dict[str, str]) -> bool:
        """
        パスの妥当性検証
        
        Args:
            paths: 検証するパス情報
            
        Returns:
            bool: すべてのパスが有効な場合True
        """
        try:
            required_paths = ['template_dir', 'output_dir']
            
            # 必須パスの存在確認
            for key in required_paths:
                if key not in paths:
                    ConfigResolver.logger.error(f"必須パスが未定義: {key}")
                    return False
                
                path = Path(paths[key])
                if not path.exists():
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        ConfigResolver.logger.info(f"ディレクトリを作成: {path}")
                    except Exception as e:
                        ConfigResolver.logger.error(f"ディレクトリ作成エラー: {e}")
                        return False
            
            # オプショナルパスの作成
            optional_paths = ['temp_dir', 'export_dir']
            for key in optional_paths:
                if key in paths:
                    path = Path(paths[key])
                    if not path.exists():
                        try:
                            path.mkdir(parents=True, exist_ok=True)
                            ConfigResolver.logger.info(f"オプショナルディレクトリを作成: {path}")
                        except Exception as e:
                            ConfigResolver.logger.warning(f"オプショナルディレクトリ作成エラー: {e}")
            
            return True
            
        except Exception as e:
            ConfigResolver.logger.error(f"パス検証エラー: {e}")
            return False

    @staticmethod
    def merge_configs(main_config: Dict[str, Any], 
                     doc_processor_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定のマージ
        
        Args:
            main_config: メインアプリケーションの設定
            doc_processor_config: ドキュメント処理の設定
            
        Returns:
            Dict[str, Any]: マージされた設定
        """
        try:
            merged = main_config.copy()
            
            # パスの解決と設定
            paths = ConfigResolver.resolve_integration_paths(main_config)
            merged['paths'] = paths
            
            # ドキュメント処理設定の追加
            # 既存の設定を上書きしないよう注意
            for key, value in doc_processor_config.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(merged[key], dict) and isinstance(value, dict):
                    # 辞書の場合は再帰的にマージ
                    merged[key] = ConfigResolver.merge_configs(merged[key], value)
            
            ConfigResolver.logger.info("設定のマージ完了")
            return merged
            
        except Exception as e:
            ConfigResolver.logger.error(f"設定マージエラー: {e}")
            raise

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """
        設定の妥当性検証
        
        Args:
            config: 検証する設定
            
        Returns:
            List[str]: エラーメッセージのリスト（空なら問題なし）
        """
        errors = []
        
        try:
            # 必須キーの確認
            required_keys = ['paths', 'db_path']
            for key in required_keys:
                if key not in config:
                    errors.append(f"必須設定が未定義: {key}")
            
            # パスの検証
            if 'paths' in config:
                if not ConfigResolver.validate_paths(config['paths']):
                    errors.append("パスの検証に失敗しました")
            
            # データベースパスの検証
            if 'db_path' in config:
                db_path = Path(config['db_path'])
                if not db_path.parent.exists():
                    try:
                        db_path.parent.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(f"データベースディレクトリの作成に失敗: {e}")
            
            return errors
            
        except Exception as e:
            ConfigResolver.logger.error(f"設定検証エラー: {e}")
            return [f"設定検証中にエラーが発生: {e}"]

    @staticmethod
    def get_config_value(config: Dict[str, Any], 
                        key_path: str, 
                        default: Any = None) -> Optional[Any]:
        """
        ネストした設定値の取得
        
        Args:
            config: 設定辞書
            key_path: ドット区切りのキーパス
            default: デフォルト値
            
        Returns:
            Any: 設定値（存在しない場合はデフォルト値）
        """
        try:
            current = config
            for key in key_path.split('.'):
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
            
        except Exception as e:
            ConfigResolver.logger.error(f"設定値取得エラー: {e}")
            return default

    @staticmethod
    def update_config_value(config: Dict[str, Any], 
                          key_path: str, 
                          value: Any) -> None:
        """
        ネストした設定値の更新
        
        Args:
            config: 設定辞書
            key_path: ドット区切りのキーパス
            value: 設定値
        """
        try:
            keys = key_path.split('.')
            current = config
            
            # 最後のキーまで辿る
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # 値を設定
            current[keys[-1]] = value
            
        except Exception as e:
            ConfigResolver.logger.error(f"設定値更新エラー: {e}")
            raise