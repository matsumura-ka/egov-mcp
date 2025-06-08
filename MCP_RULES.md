# 法令API MCP 運用ルール

## 🎯 基本方針

1. **APIレスポンス準拠の原則**
   - 全てのパラメータ設定は `@/APIレスポンス` フォルダ内の仕様書を必ず参照すること
   - APIレスポンス仕様にないパラメータは絶対に設定しない
   - レスポンスフィールド名は正確に一致させること

2. **ユーザー体験優先の原則**
   - 回答は常に日本語で提供
   - markdownコードブロックは必ず ```で括る
   - 技術的詳細よりも実用的な情報を重視

3. **効率的検索の原則**
   - 単一法令検索は可能な限り `law_id` を使用
   - キーワード検索は文脈に応じて適切に絞り込み
   - 結果が多すぎる場合は `limit` パラメータで調整
   - 現行法令のみが必要な場合は `filter_current_only: true` を活用

## 📋 API別運用指針

### 🔍 法令一覧取得API (/laws)
**レスポンス構造準拠:**
```json
{
  "total_count": number,
  "count": number,
  "laws": [
    {
      "law_info": {...},
      "revision_info": {...},
      "current_revision_info": {...}
    }
  ]
}
```

**運用ルール:**
- `law_title` での部分検索を積極活用
- `law_type` での絞り込みを適切に使用（Act, CabinetOrder, MinisterialOrdinance, Rule, Constitution）
- `limit` は状況に応じて 1-100 の範囲で設定
- `fields_only` 使用時は必ずレスポンス構造に準拠
- `filter_current_only: true` で現行有効な法令のみを取得
- `content_type` の適切な選択：
  - `summary`: 基本情報（law_revision_id含む）
  - `enhanced_summary`: 詳細情報（法令ID、本文概要含む）
  - `full`: 完全な情報

### 📚 法令履歴一覧取得API (/law_revisions)
**レスポンス構造準拠:**
```json
{
  "law_info": {...},
  "revisions": [
    {
      "law_revision_id": "string",
      "law_title": "string",
      "category": "string",
      ...
    }
  ]
}
```

**運用ルール:**
- 必ず `law_id` または `law_num` を指定
- 履歴追跡時は時系列順を意識
- `fields_only` で必要な情報のみ抽出

### 📖 法令本文取得API (/law_data)
**レスポンス構造準拠:**
```json
{
  "attached_files_info": {...},
  "law_info": {...},
  "revision_info": {...},
  "law_full_text": {...}
}
```

**運用ルール:**
- `content_type` を適切に選択：
  - `full`: 完全な情報が必要な場合
  - `body_only`: 本文のみが必要な場合
  - `summary`: 概要情報（law_revision_id含む）
  - `enhanced_summary`: 詳細概要（本文概要含む）
  - `basic_info`: メタデータのみが必要な場合
- `law_revision_id` は正確に指定
- エラー時は詳細な対処法が表示される

### 🔎 キーワード検索API (/keyword)
**レスポンス構造準拠:**
```json
{
  "total_count": number,
  "sentence_count": number,
  "next_offset": number,
  "items": [
    {
      "law_info": {...},
      "revision_info": {...},
      "sentences": [...]
    }
  ]
}
```

**運用ルール:**
- 検索キーワードは具体的かつ明確に
- `law_type`, `promulgate_era`, `promulgate_year` で適切に絞り込み
- 結果が多い場合は `limit` で調整（デフォルト100）
- ハイライト表示された `<span>` タグを活用

## 🎨 出力フォーマット規則

### 📝 構造化された情報提示
```markdown
## 🏛️ [法令名]

### 📋 基本情報
- **法令ID**: `law_id`
- **法令番号**: `law_num`
- **分類**: `category`
- **公布日**: `promulgation_date`

### 📖 関連条文
[具体的な条文内容]

### 🔗 参考情報
[必要に応じて追加情報]
```

### 🎯 検索結果の見やすい表示
- 法令名は見出しで強調
- 重要なフィールドは **太字** で表示
- コードブロックは適切にハイライト
- リスト形式で情報を整理

## ⚡ パフォーマンス最適化

### 🔧 fields_only の効果的活用
- 必要な情報のみを取得してレスポンス時間を短縮
- ネストしたフィールド指定時は正確な階層構造を指定
- 例: `["law_info.law_id", "revision_info.law_title", "revision_info.law_revision_id"]`
- `enhanced_summary` との組み合わせで最適化

### 📊 適切な limit 設定
- 探索的検索: 5-10件
- 詳細調査: 20-50件
- 網羅的検索: 100件（最大）

### 🎯 効率的な検索戦略
1. **特定法令検索**: `law_id` → `law_revisions` → `law_data`
2. **テーマ検索**: `keyword` → 絞り込み → 詳細取得
3. **分野検索**: `laws` + `category` → 詳細取得
4. **現行法令特化**: `filter_current_only: true` で有効法令のみ
5. **効率的概要取得**: `enhanced_summary` でID付き詳細情報

### 🆕 新機能活用ガイド

#### 📍 現行法令フィルタリング
```json
{
  "law_title": "会社法",
  "filter_current_only": true,
  "content_type": "summary"
}
```
- 廃止された法令を除外し、現在有効な法令のみ取得
- 法令検索の精度向上とノイズ除去

#### 📊 拡張サマリーモード
```json
{
  "law_revision_id": "417AC0000000086",
  "content_type": "enhanced_summary"
}
```
- 法令IDと本文概要を含む詳細情報
- APIレスポンス量を最適化しつつ必要情報を確保

## 🛡️ エラーハンドリング

### ⚠️ 一般的なエラー対処
- 検索結果0件: キーワードや条件を緩和して再検索
- パラメータエラー: APIレスポンス仕様を再確認
- タイムアウト: limit を減らして再実行

### 🚨 404エラー対応（改善済み）
- 法令ID/履歴IDが見つからない場合の詳細メッセージ表示
- 具体的な対処法の自動提案：
  - 法令名での検索は `get_laws` 使用推奨
  - キーワード検索は `search_keyword` 使用推奨
  - リクエストURLの表示による問題特定支援

### 🔄 代替手段の提案
- 直接検索で見つからない場合はキーワード検索を提案
- 古い法令の場合は履歴検索を活用
- 関連法令の提案も積極的に実施
- `filter_current_only` で現行法令に絞り込み提案

## 📈 継続的改善

### 📝 ログとモニタリング
- よく使用される検索パターンを記録
- エラー頻度の高いクエリを特定
- ユーザーフィードバックを収集

### 🔄 定期的なルール見直し
- APIレスポンス構造の変更をチェック
- 新機能追加時のルール更新
- ユーザー利用パターンに基づく最適化

---

## 🎉 まとめ

このMCPルールにより、法令APIを**正確**で**効率的**、かつ**ユーザーフレンドリー**な方法で活用できます。

### 🚀 主要改善点
- **現行法令フィルタリング**: 有効な法令のみを効率的に取得
- **拡張サマリー機能**: 必要な情報を最適化されたボリュームで提供  
- **改善されたエラーハンドリング**: 具体的な対処法で問題解決を支援
- **汎用性重視**: 特定法令に依存しない柔軟なシステム設計

常にAPIレスポンス仕様に準拠し、ユーザーの検索意図を最大限に理解した上で、最適な情報提供を心がけましょう。新機能を積極的に活用し、より効率的な法令検索体験を提供することを目指します。 