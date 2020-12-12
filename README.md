# mssql-migrate

## 概要
SQL Server 専用の DB マイグレーションツール。  
python 3.8 製。

## 特徴
* Microsoft SQL Server のみ対応。
* 設定ファイルもマイグレーションファイルも .py ファイル。  
  Python コードで SQL や設定を書くことができる。  
  環境変数を読み込ませて SQL に組み込むこともできる。
* スキーマを自動作成できる。  
  スキーマは初回実行時に作成される。  
  ここで作成されたスキーマはマイグレーション管理の対象外。  
  一番初めに実行されるため、ここで作成したスキーマ上に管理テーブルを作成することも可能。

## 必須ライブラリ
* `pyodbc`
* あとは python 3.8 標準のはず。


## 使用方法

### 標準フォルダ構成

```
<your-work-directory>/
  ├ migration/          ... マイグレーションファイルを置くディレクトリ
  ├ config.py           ... 設定ファイル。[./migrate/config.py](./migrate/config.py) をコピー
  └ mssql-migrate.py    ... ツール本体。[./migrate/mssql-migrate.py](./migrate/mssql-migrate.py) をコピー
```

### 設定

`config.py` に記述する。  

#### `config.py` の内容
```py:config.py
MSSQL_MIGRATE_FILE_DIR  = "マイグレーションファイルを置くディレクトリ。絶対パス or configファイル からの相対パス。"
MSSQL_MIGRATE_DB_HOST   = "DBホスト名 or IPアドレス"
MSSQL_MIGRATE_DB_PORT   = "ポート番号"
MSSQL_MIGRATE_DB_NAME   = "DB名"
MSSQL_MIGRATE_DB_USER   = "DBユーザー"
MSSQL_MIGRATE_DB_PASS   = "DBパスワード"
MSSQL_MIGRATE_SCHEMA    = "自動作成するスキーマ名（省略可）。カンマ区切りの文字列 or list"
MSSQL_MIGRATE_TABLE     = "マイグレーション管理テーブル名。自動作成される。"
```

#### 設定ファイルの指定方法

`config.py` のファイル名・パスは変更可能。  
指定方法は以下の３通り。上から優先。
1. コマンドラインパラメータ  
   `--config <PATH>`
1. 環境変数  
   `MSSQL_MIGRATE_CONFIG=<PATH>`
1. デフォルト  
    実行ディレクトリの `config.py`




### 実行方法
詳しい使い方はヘルプ `--help` で。
```bash
# ヘルプ表示
mssql-migrate.py --help
mssql-migrate.py <sub-command> --help

# マイグレーションファイルのテンプレートを生成
mssql-migrate.py new <NAME>

#
# config の `MSSQL_MIGRATE_FILE_DIR` で指定したディレクトリに
# テンプレートファイルが作成されるので、SQLを記述する。
# 

# 現在のマイグレーション適用状況を確認
mssql-migrate.py show

# マイグレーション実行
#    default: 未適用のマイグレーションファイルを全て適用
mssql-migrate.py up

# リグレッション実行
#   default: １段階戻す
mssql-migrate.py down

```


## サンプル実行

Dockerで以下のコンテナを起動し、`mssql-migrate` を実行できます。
* SQL Server
* `mssql-migrate` を実行する Alpine Linux

### 前提
Docker がインストールされていること。

### 実行方法

このリポジトリを `clone` したディレクトリで実施。

```bash

# 初回のみ実行
docker-compose build

# dockerコンテナ起動 ＆ Alpine Linux にログイン
docker-compose run --rm migrate-sample


# ------------------------------------
# 以下、Dockerコンテナ内
# ------------------------------------

# ヘルプ表示
python3 mssql-migrate.py --help
python3 mssql-migrate.py up --help

# 現在のマイグレーション適用状況を参照
python3 mssql-migrate.py show

# マイグレーション
python3 mssql-migrate.py up

# リグレッション
python3 mssql-migrate.py down


# おまけ： コマンドラインで SQL Server に接続するときは
sqlcmd -S "${MSSQL_MIGRATE_DB_HOST},${MSSQL_MIGRATE_DB_PORT}" -U "${MSSQL_MIGRATE_DB_USER}" -P "${MSSQL_MIGRATE_DB_PASS}" -d "${MSSQL_MIGRATE_DB_NAME}"


# コンテナからログアウト
exit


# ------------------------------------
# 以下、ローカル環境
# ------------------------------------

# コンテナを停止
docker-compose down

```
