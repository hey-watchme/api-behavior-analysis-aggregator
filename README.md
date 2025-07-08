# SED分析API システム v2.0 - Supabase統合版

音響イベント検出（SED）データの収集・集計をSupabaseデータベース統合で行うFastAPIベースのREST APIサービスです。

## 📋 システム概要

**🚀 v2.0の主要変更点:**
- ✅ **完全Supabase統合**: JSONファイル → データベース直接連携
- ✅ **効率化されたデータ構造**: 構造化オブジェクト形式
- ✅ **ローカルファイル廃止**: クラウドファーストアーキテクチャ

**🌐 システム構成:**
- **データ取得**: Supabase `behavior_yamnet` テーブルから直接取得
- **データ集計**: 音響イベントの自動集計・ランキング生成
- **データ保存**: Supabase `behavior_summary` テーブルに直接保存
- **API提供**: FastAPIによるREST API

## 🗄️ データベース構造

### behavior_yamnet テーブル（データソース）
```sql
CREATE TABLE behavior_yamnet (
  device_id     text NOT NULL,
  date          date NOT NULL,
  time_block    text NOT NULL CHECK (time_block ~ '^[0-2][0-9]-[0-5][0-9]$'),
  events        jsonb NOT NULL,
  PRIMARY KEY (device_id, date, time_block)
);
```

**eventsカラムの構造:**
```json
[
  {"label": "Speech", "prob": 0.98},
  {"label": "Silence", "prob": 1.0},
  {"label": "Inside, small room", "prob": 0.31}
]
```

### behavior_summary テーブル（集計結果保存先）
```sql
CREATE TABLE behavior_summary (
  device_id       text NOT NULL,
  date            date NOT NULL,
  summary_ranking jsonb NOT NULL,  -- 全体ランキング
  time_blocks     jsonb NOT NULL,  -- スロット別の出現数
  PRIMARY KEY (device_id, date)
);
```

**summary_rankingの構造:**
```json
[
  {"event": "Speech", "count": 42},
  {"event": "Silence", "count": 38},
  {"event": "other", "count": 156}
]
```

**time_blocksの構造:**
```json
{
  "00-00": [
    {"event": "Speech", "count": 3},
    {"event": "Silence", "count": 2}
  ],
  "00-30": null,
  "01-00": [
    {"event": "Music", "count": 1}
  ]
}
```

## 📋 システム要件

**🐍 Python環境:**
- Python 3.11.8以上
- FastAPI + Uvicorn（APIサーバー）
- Supabase Python クライアント
- python-dotenv（環境変数管理）

**🗄️ データベース:**
- Supabase プロジェクト
- behavior_yamnet、behavior_summary テーブル

**📁 プロジェクト構成:**
```
api_sed-aggregator_v1/
├── api_server.py              # メインAPIサーバー
├── sed_aggregator.py          # Supabase統合データ処理モジュール
├── upload_sed_summary.py      # アップロードモジュール（レガシー）
├── test_supabase.py          # テストスクリプト
├── .env                      # Supabase認証情報
├── requirements.txt          # 依存関係
└── README.md                # このファイル
```

## 🚀 セットアップ

### 1️⃣ 依存関係インストール
```bash
pip install -r requirements.txt
```

### 2️⃣ 環境変数設定
`.env`ファイルを作成してSupabase認証情報を設定:
```env
SUPABASE_URL=https://qvtlwotzuzbavrzqhyvt.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3️⃣ APIサーバー起動
```bash
# 開発環境（推奨）
python api_server.py

# または
uvicorn api_server:app --reload --host 0.0.0.0 --port 8010
```

APIサーバーは `http://localhost:8010` で起動します。

### 4️⃣ 接続確認
```bash
curl http://localhost:8010/health
```

## 🌐 API エンドポイント

### 📊 SED分析API

#### **1. 分析開始** `POST /analysis/sed`
**機能**: Supabaseからのデータ取得・集計・保存をバックグラウンドで実行

**リクエスト:**
```bash
POST /analysis/sed
Content-Type: application/json

{
  "device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0",
  "date": "2025-07-07"
}
```

**レスポンス（成功）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "message": "d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-07 の分析を開始しました"
}
```

#### **2. 分析状況確認** `GET /analysis/sed/{task_id}`
**機能**: タスクの進捗状況と結果を取得

**レスポンス（完了）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "分析完了",
  "progress": 100,
  "result": {
    "message": "データはSupabaseのbehavior_summaryテーブルに保存されました",
    "device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0",
    "date": "2025-07-07"
  }
}
```

#### **3. 全タスク一覧** `GET /analysis/sed`
**機能**: 実行中・完了済みの全タスクを一覧表示

#### **4. タスク削除** `DELETE /analysis/sed/{task_id}`
**機能**: 完了・失敗したタスクを削除

#### **5. ヘルスチェック** `GET /health` | `GET /`
**機能**: API稼働状況の確認

## 💻 使用例

### コマンドライン実行
```bash
# データ集計の直接実行
python sed_aggregator.py d067d407-cf73-4174-a9c1-d91fb60d64d0 2025-07-07

# テスト実行
python test_supabase.py
```

### Python クライアント
```python
import requests

# 分析開始
response = requests.post("http://localhost:8010/analysis/sed", json={
    "device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0",
    "date": "2025-07-07"
})

task_id = response.json()["task_id"]

# 結果確認
result = requests.get(f"http://localhost:8010/analysis/sed/{task_id}")
print(result.json())
```

### cURL例
```bash
# 分析開始
TASK_ID=$(curl -s -X POST "http://localhost:8010/analysis/sed" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0", "date": "2025-07-07"}' \
  | jq -r '.task_id')

# 結果確認
curl "http://localhost:8010/analysis/sed/$TASK_ID" | jq '.'
```

## 📊 データフォーマット

### 集計結果例（behavior_summaryテーブル）

```json
{
  "summary_ranking": [
    {"event": "other", "count": 50},
    {"event": "Silence", "count": 7},
    {"event": "Speech", "count": 7},
    {"event": "Inside, small room", "count": 3},
    {"event": "Whack, thwack", "count": 2},
    {"event": "Arrow", "count": 2}
  ],
  "time_blocks": {
    "00-00": [
      {"event": "Sound effect", "count": 1},
      {"event": "Inside, small room", "count": 1},
      {"event": "Whack, thwack", "count": 1},
      {"event": "Explosion", "count": 1}
    ],
    "00-30": null,
    "09-00": [
      {"event": "Speech", "count": 1},
      {"event": "Animal", "count": 2}
    ],
    "18-30": [
      {"event": "Silence", "count": 1},
      {"event": "Speech", "count": 1}
    ]
  }
}
```

## 🔧 技術仕様

### 処理フロー
1. **データ取得**: Supabase `behavior_yamnet` テーブルから該当日のデータを取得
2. **データ集計**: 音響イベントラベルを抽出・カウント
3. **ランキング生成**: トップ5 + その他の summary_ranking を作成
4. **時間別集計**: 48スロット別の time_blocks を作成
5. **データ保存**: Supabase `behavior_summary` テーブルにUPSERT

### パフォーマンス
- **同時処理**: バックグラウンドタスクによる非同期処理
- **データベース効率**: 単一クエリでの一括取得
- **メモリ効率**: ストリーミング処理とガベージコレクション

### エラーハンドリング
- Supabase接続エラーの自動検出
- データ不整合の自動処理
- 詳細なログ出力とエラーレポート

## ⚠️ トラブルシューティング

### よくあるエラー

**Supabase接続エラー**
```
ValueError: SUPABASE_URLおよびSUPABASE_KEYが設定されていません
```
→ `.env`ファイルの認証情報を確認

**データなしエラー**
```
⚠️ 取得できたデータがありません
```
→ 指定したdevice_id/dateのデータがbehavior_yamnetテーブルに存在するか確認

**権限エラー**
```
❌ Supabase保存エラー: ...
```
→ Supabaseキーの権限とテーブルのRLSポリシーを確認

## 🆕 v2.0の利点

### 従来版（v1.0）との比較
| 項目 | v1.0（JSONファイル版） | v2.0（Supabase統合版） |
|------|----------------------|----------------------|
| データソース | Vault API (HTTP) | Supabase (Database) |
| 保存先 | ローカルファイル | Supabaseテーブル |
| データ形式 | 文字列配列 | 構造化オブジェクト |
| パフォーマンス | 48並列HTTP | 単一DB接続 |
| 信頼性 | ネットワーク依存 | データベース高可用性 |
| 拡張性 | ファイルベース制限 | SQLベース無制限 |

### メリット
- ✅ **高速化**: 並列HTTP → 単一DBクエリ
- ✅ **信頼性向上**: ファイルシステム → マネージドDB
- ✅ **構造化データ**: 文字列 → JSONオブジェクト
- ✅ **スケーラビリティ**: 無制限のデータ処理
- ✅ **統合性**: 他システムとのシームレス連携

## 📞 サポート

**API仕様の詳細:**
- OpenAPI/Swagger UI: `http://localhost:8010/docs`
- ReDoc: `http://localhost:8010/redoc`

**データベース設計:**
- behavior_yamnet: 音響イベント生データ
- behavior_summary: 集計済みサマリーデータ

**開発者向けサポート:**
- Supabase統合ベストプラクティス
- 非同期処理の実装ガイド
- データベース最適化手法