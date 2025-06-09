# e-Gov法令API用MCPサーバー

日本の法令を検索・取得するためのMCPサーバーです。

## プロジェクト構成

| ファイル/ディレクトリ | 用途 |
|---------------------|------|
| **MCP_RULES.md** | 法令API MCPの運用ルール・ベストプラクティス集 |
| **APIレスポンス/** | e-Gov法令APIのレスポンス仕様書 |
| **egov_mcp/** | MCPサーバーの実装コード |

## 利用可能なツール

| ツール名 | 機能 |
|---------|------|
| **get_laws** | 法令の検索・一覧取得 |
| **get_law_data** | 法令本文の取得 |
| **get_law_revisions** | 改正履歴の確認 |
| **search_keyword** | キーワード検索 |
| **get_law_file** | PDF/DOCX/XMLファイルの取得 |
| **get_attachment** | 添付ファイルの取得 |

## セットアップ

### Dockerで実行（推奨）

**必要な環境:**
- Docker

```bash
git clone https://github.com/matsumura-ka/egov-mcp
cd egov-mcp
make docker-run
```

### ローカルで実行

**必要な環境:**
- Python 3.10以上
- Poetry

**手順:**

```bash
# 1. プロジェクトをダウンロード
git clone https://github.com/matsumura-ka/egov-mcp
cd egov-mcp

# 2. 依存関係をインストール（シンボリックリンクも自動作成）
make install

# 3. 動作確認（オプション）
make run
```

**`make install`の効果:**
- 依存関係のインストール
- `~/egov-mcp-link`にシンボリックリンクを作成
- MCP設定情報を表示

## MCPクライアントでの設定

### ローカル実行用（推奨・最も簡単）

`make install`実行後、設定ファイルに以下を追加：

```json
{
  "mcpServers": {
    "egov-mcp": {
      "command": "poetry",
      "args": ["run", "-C", "/path/to/egov-mcp", "egov-mcp"],
      "env": {}
    }
  }
}
```

**注意：** `/path/to/egov-mcp`を実際のプロジェクトパスに変更してください。
例：`/Users/yourname/development/egov-mcp`

**代替設定（直接パス指定）：**

```json
{
  "mcpServers": {
    "egov-mcp": {
      "command": "poetry",
      "args": ["run", "-C", "/path/to/egov-mcp", "python", "egov_mcp/main.py"],
      "env": {}
    }
  }
}
```

### Docker実行用

```json
{
  "mcpServers": {
    "egov-mcp": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "egov-mcp"],
      "env": {}
    }
  }
}
```

## 使用例

**法改正の影響確認**
- 令和5年度税制改正における法人税法の変更点と会計処理への影響を確認したい

**会計基準と法令の関係**
- リース会計基準の変更に伴う会社法上の計算書類への影響と法人税法の取扱いを確認したい

**実務で重要な法令確認**
- 電子帳簿保存法の最新要件と会計システムの対応義務について詳しく確認したい

## よくある問題

**MCPクライアントで認識されない**
- 設定ファイルのJSON記法を確認
- クライアントを再起動

**法令が見つからない**
- 正確な法令名で検索
- キーワード検索を試す

**エラーが出る**
- より具体的で限定的な質問に変更

## 注意事項

- 政府のe-Gov法令APIを使用
- 重要な判断には最新の公式情報を確認してください

## ライセンス

MIT License 