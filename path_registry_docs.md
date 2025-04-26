# パス管理ドキュメント

## 概要

ProjectSuiteアプリケーションでは、パスの管理に`PathRegistry`クラスを使用しています。
このドキュメントでは、パス管理の仕組みと使用方法について解説します。

## PathRegistryの基本

`PathRegistry`は単一情報源（Single Source of Truth）として機能し、アプリケーション全体でパスを一元管理します。
これにより、複数のモジュール間でパスの一貫性を保ち、パス変更時の影響範囲を制限できます。

### 主要機能

- パスの登録・取得
- ディレクトリの存在確認・作成
- エイリアス管理（同じパスを複数の名前で参照）
- パス診断・自動修復

## パスキーとエイリアス

### 主要パスキー

| パスキー | 説明 | デフォルト値 |
|----------|------|-------------|
| OUTPUT_BASE_DIR | プロジェクト出力先の基本ディレクトリ | ~/Desktop/projects |
| PROJECTS_DIR | OUTPUT_BASE_DIRのエイリアス（後方互換性用） | ~/Desktop/projects |
| USER_DATA_DIR | ユーザーデータディレクトリ | ~/Documents/ProjectSuite |
| DB_PATH | データベースファイルパス | USER_DATA_DIR/ProjectManager/data/projects.db |

### エイリアス関係