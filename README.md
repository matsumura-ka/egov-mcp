# e-Gov法令API用MCPサーバー

e-Gov法令APIにアクセスするためのMCP（Model Context Protocol）サーバーです。

## 概要

このMCPサーバーは以下の機能を提供します：

- 法令一覧の取得
- 法令本文データの取得
- 法令履歴の取得
- キーワード検索
- 添付ファイルの取得
- 法令ファイル（PDF、DOCX、XML）の取得

## 利用可能な機能

### ツール一覧

1. **get_laws** - 法令一覧を取得
2. **get_law_data** - 特定の法令の本文データを取得
3. **get_law_revisions** - 特定の法令の履歴一覧を取得
4. **search_keyword** - 法令本文内のキーワード検索
5. **get_attachment** - 法令の添付ファイルを取得
6. **get_law_file** - 法令本文ファイルを取得

## セットアップ

### 必要な環境

- Python 3.10以上
- Poetry（推奨）
- Docker（Docker経由で実行する場合）

### インストール

```bash
# 依存関係をインストール
make install

# または直接Poetry経由でインストール
poetry install
```

## 使用方法

### 1. Dockerで実行（推奨）

最も簡単な方法です：

```bash
# Dockerコンテナでサーバーを実行
make docker-run
```

これにより以下が自動的に実行されます：
- Dockerイメージのビルド
- ポート8000でのサーバー起動

### 2. ローカルで直接実行

```bash
# MCPサーバーを直接実行
make run

# または
poetry run python egov_mcp/main.py
```

### 3. 開発者向けコマンド

```bash
# コードのフォーマット
make format

# コードの静的解析
make check
# または
make lint

# Dockerイメージのクリーンアップ
make clean
```

### 利用可能なコマンド一覧

```bash
# すべてのコマンドを表示
make help
```

## MCPクライアントでの使用例

このサーバーはClaude DesktopなどのMCPクライアントから利用できます。

### Claude Desktop設定例

```json
{
  "mcpServers": {
    "egov-mcp": {
      "command": "docker",
      "args": ["run", "-p", "8000:8000", "egov-mcp"]
    }
  }
}
```

### 使用例

```
# 憲法を検索
search_keyword(keyword="憲法")

# 特定の法令の詳細を取得
get_laws(law_title="民法")

# 法令の本文を取得
get_law_data(law_revision_id="法令履歴ID")
```

## 開発情報

### プロジェクト構造

```
egov-mcp/
├── egov_mcp/
│   ├── __init__.py
│   └── main.py          # メインのMCPサーバー
├── pyproject.toml       # Poetry設定
├── Dockerfile          # Docker設定
├── Makefile            # 便利なコマンド
└── README.md
```

### API詳細

このMCPサーバーは e-Gov法令API (https://laws.e-gov.go.jp/api/2) を使用しています。

## ライセンス

MIT License

## 貢献

プルリクエストやissueの報告を歓迎します。 