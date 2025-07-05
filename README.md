# SED分析API システム - 完全仕様書

音響イベント検出（SED）データの収集・集計・アップロードを行うFastAPIベースのREST APIサービスです。

## 📋 コードベース調査結果

### 🔍 システム構成分析
**調査日**: 2025-06-29  
**ファイル数**: 6個  
**コード行数**: 約1,200行  
**言語**: Python 3.11.8+  
**フレームワーク**: FastAPI + aiohttp

### 📊 主要機能の詳細分析

#### 🎯 **核心機能**
1. **音響イベント検出（SED）データ処理**
   - 30分スロット×48個（24時間分）の並列データ取得
   - 音響イベントラベルの自動抽出・分類
   - トップ5ランキング + その他カテゴリの自動生成

2. **バックグラウンドタスク処理**
   - 非同期タスク実行（FastAPI BackgroundTasks）
   - リアルタイム進捗監視（0-100%）
   - タスク状況管理（started/running/completed/failed）

3. **Vault API統合**
   - SED専用データ取得: `https://api.hey-watch.me/download-sed`
   - Vault APIへのアップロード: `https://api.hey-watch.me/upload/analysis/sed-summary`
   - SSL証明書検証無効化対応

#### 📁 **ファイル別機能分析**

**api_server.py:229行** - メインAPIサーバー
- FastAPIアプリケーション（ポート8010）
- 5つのエンドポイント提供
- UUIDベースのタスク管理
- エラーハンドリング付きバックグラウンド処理

**sed_aggregator.py:263行** - データ集約エンジン
- Vault APIからの並列HTTP処理（最大30並列接続）
- 音響イベント再帰的ラベル抽出
- 時間ブロック別データ構造化
- ローカルファイル保存（JSON形式）

**upload_sed_summary.py:273行** - アップロード処理
- Vault APIへのFormDataアップロード
- 全ファイル/特定ファイル両対応
- 成功・失敗詳細レポート機能
- SSL証明書問題の自動回避

**example_usage.py:131行** - APIクライアント実装例
- 完全な使用フロー実装
- ヘルスチェック機能付き
- エラーハンドリング例
- 結果表示フォーマット例

#### 🔧 **技術仕様詳細**

**依存ライブラリ**
```python
fastapi>=0.104.0      # REST APIフレームワーク
uvicorn>=0.24.0       # ASGIサーバー
pydantic>=2.5.0       # データバリデーション
aiohttp>=3.8.0,<4.0.0 # 非同期HTTPクライアント
```

**処理能力**
- 同時並列処理: 最大48並列HTTP接続
- タイムアウト設定: 30秒/リクエスト
- SSL証明書検証: 環境変数制御可能
- メモリ効率: ストリーミング処理対応

**データ処理フロー**
1. Vault APIからの並列取得 → 2. JSON解析 → 3. ラベル抽出 → 4. 集計処理 → 5. ファイル保存 → 6. Vault APIへアップロード

## ⚠️ 重要: ファイル依存関係
**APIサーバー（`api_server.py`）を動作させるには、以下の3ファイルが必須です：**
- 📁 `api_server.py` - メインAPIサーバー
- 📁 `sed_aggregator.py` - データ処理モジュール (**必須依存**)
- 📁 `upload_sed_summary.py` - アップロードモジュール (**必須依存**)

## 🎯 システム概要

**🌐 REST API**: FastAPIベースの非同期APIサーバー  
**📥 データ収集**: Vault API上のSEDファイル（最大48個の30分スロット）を非同期並列取得  
**📊 データ集計**: 音響イベントラベルの自動抽出・集計処理  
**📤 データアップロード**: Vault APIへ自動アップロード  
**🔄 バックグラウンド処理**: 長時間処理の非同期実行とタスク管理

## 📋 システム要件

**🐍 Python環境:**
- Python 3.11.8以上
- FastAPI + Uvicorn（APIサーバー）
- aiohttp（HTTP非同期クライアント）
- asyncio（非同期処理）

**🌐 ネットワーク:**
- SED専用Vault API `https://api.hey-watch.me/download-sed` へのHTTPS接続
- 30分スロット×48個の並列リクエスト対応

**💾 ストレージ:**
- ローカルディスク: `/Users/kaya.matsumoto/data/data_accounts/`
- 書き込み権限必須

**📁 プロジェクト構成:**
```
api_sed-aggregator_v1/
├── api_server.py              # メインAPIサーバー（必須）
├── sed_aggregator.py          # データ処理モジュール（必須）
├── upload_sed_summary.py      # アップロードモジュール（必須）
├── example_usage.py           # 使用例（オプション）
├── requirements.txt           # 依存関係
└── README.md                 # このファイル
```

## 🚀 セットアップ

### 1️⃣ 依存関係インストール
```bash
pip install -r requirements.txt
```

### 2️⃣ ファイル構成の確認
⚠️ **APIサーバー起動前に、必須ファイルが揃っていることを確認してください：**

```bash
ls -la
# 以下のファイルが必要です：
# - api_server.py (メイン)
# - sed_aggregator.py (必須依存)
# - upload_sed_summary.py (必須依存)
```

### 3️⃣ APIサーバー起動
```bash
# 開発環境（推奨）
python api_server.py

# または
uvicorn api_server:app --reload --host 0.0.0.0 --port 8010

# 本番環境
uvicorn api_server:app --host 0.0.0.0 --port 8010 --workers 4
```

APIサーバーは `http://localhost:8010` で起動します。

### 4️⃣ 接続確認
```bash
curl http://localhost:8010/health
```

## 🌐 API エンドポイント詳細仕様

### 📊 SED分析API

#### **1. 分析開始** `POST /analysis/sed`
**機能**: SED分析をバックグラウンドで開始し、タスクIDを返却

**リクエスト:**
```bash
POST /analysis/sed
Content-Type: application/json

{
  "device_id": "device123",    # 必須: デバイス識別子
  "date": "2025-06-21"     # 必須: 分析対象日（YYYY-MM-DD形式）
}
```

**レスポンス（成功）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "message": "device123/2025-06-21 の分析を開始しました"
}
```

**レスポンス（エラー）:**
```json
{
  "detail": "日付はYYYY-MM-DD形式で指定してください"
}
```

#### **2. 分析状況確認** `GET /analysis/sed/{task_id}`
**機能**: 指定したタスクの進捗状況と結果を取得

**リクエスト:**
```bash
GET /analysis/sed/550e8400-e29b-41d4-a716-446655440000
```

**レスポンス（処理中）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "データ収集・集計中...",
  "progress": 25,
  "device_id": "device123",
  "date": "2025-06-21",
  "created_at": "2025-06-29T10:30:00.000000"
}
```

**レスポンス（完了）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "分析完了",
  "progress": 100,
  "result": {
    "analysis": {
      "summary_ranking": [
        {"event": "Speech", "count": 84},
        {"event": "Explosion", "count": 18}
      ],
      "time_blocks": {...}
    },
    "upload": {"success": 1, "failed": 0, "total": 1},
    "total_events": 300,
    "output_path": "/Users/kaya.matsumoto/data/data_accounts/device123/2025-06-21/sed-summary/result.json"
  }
}
```

**レスポンス（失敗）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "message": "分析中にエラーが発生しました",
  "progress": 100,
  "error": "接続エラー: タイムアウト"
}
```

#### **3. 全タスク一覧** `GET /analysis/sed`
**機能**: 実行中・完了済みの全タスクを一覧表示

**リクエスト:**
```bash
GET /analysis/sed
```

**レスポンス:**
```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "device_id": "device123",
      "date": "2025-06-21",
      "progress": 100
    },
    {
      "task_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "running",
      "device_id": "device456",
      "date": "2025-06-22",
      "progress": 50
    }
  ],
  "total": 2
}
```

#### **4. タスク削除** `DELETE /analysis/sed/{task_id}`
**機能**: 完了・失敗したタスクを削除（実行中タスクは削除不可）

**リクエスト:**
```bash
DELETE /analysis/sed/550e8400-e29b-41d4-a716-446655440000
```

**レスポンス（成功）:**
```json
{
  "message": "タスク 550e8400-e29b-41d4-a716-446655440000 を削除しました"
}
```

**レスポンス（エラー）:**
```json
{
  "detail": "実行中のタスクは削除できません"
}
```

#### **5. ヘルスチェック** `GET /health` | `GET /`
**機能**: API稼働状況の確認

**リクエスト:**
```bash
GET /health
```

**レスポンス:**
```json
{
  "status": "healthy"
}
```

**リクエスト:**
```bash
GET /
```

**レスポンス:**
```json
{
  "service": "SED分析API",
  "status": "running",
  "timestamp": "2025-06-29T10:30:00.000000"
}
```

## 📱 実用的な使用例

### Python クライアント（完全版）
```python
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

class SEDAnalysisClient:
    """SED分析APIクライアント（エラーハンドリング強化版）"""
    
    def __init__(self, base_url="http://localhost:8010"):
        self.base_url = base_url
    
    async def health_check(self):
        """APIの稼働状況を確認"""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        return True
                    return False
        except Exception as e:
            print(f"❌ API接続エラー: {e}")
            return False
    
    async def start_analysis(self, device_id, date):
        """分析を開始してタスクIDを取得"""
        try:
            data = {"device_id": device_id, "date": date}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/analysis/sed",
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ 分析開始: {result['message']}")
                        return result["task_id"]
                    else:
                        error = await response.json()
                        print(f"❌ 分析開始エラー: {error['detail']}")
                        return None
        except Exception as e:
            print(f"❌ 分析開始エラー: {e}")
            return None
    
    async def get_status(self, task_id):
        """タスク状況を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/analysis/sed/{task_id}"
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        print(f"❌ タスクが見つかりません: {task_id}")
                        return None
                    else:
                        error = await response.text()
                        print(f"❌ 状況取得エラー: {error}")
                        return None
        except Exception as e:
            print(f"❌ 状況取得エラー: {e}")
            return None
    
    async def wait_for_completion(self, task_id, max_wait=600):
        """分析完了まで待機（タイムアウト付き）"""
        print(f"⏳ 分析完了を待機中... (最大{max_wait}秒)")
        
        start_time = datetime.now()
        while True:
            status = await self.get_status(task_id)
            if not status:
                return None
            
            # 進捗表示
            elapsed = (datetime.now() - start_time).seconds
            print(f"📊 進捗: {status['progress']}% - {status['message']} ({elapsed}秒経過)")
            
            if status['status'] == 'completed':
                print("🎉 分析完了!")
                return status
            elif status['status'] == 'failed':
                print(f"❌ 分析失敗: {status.get('error', '不明なエラー')}")
                return status
            
            if elapsed >= max_wait:
                print("⏰ タイムアウト: 分析が時間内に完了しませんでした")
                return None
            
            await asyncio.sleep(2)  # 2秒間隔でチェック
    
    async def run_full_analysis(self, device_id, date):
        """完全な分析フローを実行"""
        print(f"🚀 SED分析開始: {device_id} / {date}")
        
        # 1. ヘルスチェック
        if not await self.health_check():
            print("❌ APIサーバーが応答しません")
            return None
        
        # 2. 分析開始
        task_id = await self.start_analysis(device_id, date)
        if not task_id:
            return None
        
        # 3. 完了まで待機
        result = await self.wait_for_completion(task_id)
        if not result:
            return None
        
        # 4. 結果処理
        if result['status'] == 'completed' and 'result' in result:
            analysis_data = result['result']['analysis']
            upload_data = result['result']['upload']
            
            print(f"\n📊 分析結果:")
            print(f"  📁 出力ファイル: {result['result']['output_path']}")
            print(f"  🎵 総イベント数: {result['result']['total_events']}")
            print(f"  ☁️ アップロード: 成功 {upload_data['success']}, 失敗 {upload_data['failed']}")
            
            # トップ音響イベント表示
            if analysis_data['summary_ranking']:
                print(f"\n🏆 上位音響イベント:")
                for i, item in enumerate(analysis_data['summary_ranking'][:5], 1):
                    print(f"  {i}. {item['event']}: {item['count']}回")
            
            return result
        
        return result

# 使用例
async def main():
    client = SEDAnalysisClient()
    
    # 単体分析実行
    result = await client.run_full_analysis("device123", "2025-06-21")
    
    # 複数日分析実行
    dates = ["2025-06-20", "2025-06-21", "2025-06-22"]
    for date in dates:
        print(f"\n{'='*50}")
        await client.run_full_analysis("device123", date)
        await asyncio.sleep(1)  # 1秒間隔

# 実行
if __name__ == "__main__":
    asyncio.run(main())
```

### Bash/curl スクリプト
```bash
#!/bin/bash
# SED分析 実行スクリプト

API_BASE="http://localhost:8010"
USER_ID="device123"
DATE="2025-06-21"

echo "🚀 SED分析開始: $USER_ID / $DATE"

# 1. ヘルスチェック
echo "🔍 APIヘルスチェック..."
if ! curl -s -f "$API_BASE/health" > /dev/null; then
    echo "❌ APIサーバーが応答しません"
    exit 1
fi
echo "✅ API稼働中"

# 2. 分析開始
echo "📊 分析開始..."
RESPONSE=$(curl -s -X POST "$API_BASE/analysis/sed" \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"$USER_ID\", \"date\": \"$DATE\"}")

TASK_ID=$(echo "$RESPONSE" | jq -r '.task_id')
if [ "$TASK_ID" = "null" ]; then
    echo "❌ 分析開始エラー:"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

echo "✅ 分析開始成功: Task ID = $TASK_ID"

# 3. 進捗監視
echo "⏳ 分析完了まで待機..."
while true; do
    STATUS_RESPONSE=$(curl -s "$API_BASE/analysis/sed/$TASK_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
    PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress')
    MESSAGE=$(echo "$STATUS_RESPONSE" | jq -r '.message')
    
    echo "📊 進捗: $PROGRESS% - $MESSAGE"
    
    if [ "$STATUS" = "completed" ]; then
        echo "🎉 分析完了!"
        echo "$STATUS_RESPONSE" | jq '.result'
        break
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ 分析失敗:"
        echo "$STATUS_RESPONSE" | jq '.error'
        exit 1
    fi
    
    sleep 2
done

echo "✅ SED分析が正常に完了しました"
```

### JavaScript（Node.js）
```javascript
const axios = require('axios');

class SEDAnalysisClient {
    constructor(baseUrl = 'http://localhost:8010') {
        this.baseUrl = baseUrl;
    }

    async healthCheck() {
        try {
            const response = await axios.get(`${this.baseUrl}/health`, { timeout: 5000 });
            return response.status === 200;
        } catch (error) {
            console.log(`❌ API接続エラー: ${error.message}`);
            return false;
        }
    }

    async startAnalysis(userId, date) {
        try {
            const response = await axios.post(`${this.baseUrl}/analysis/sed`, {
                device_id: userId,
                date: date
            });
            console.log(`✅ 分析開始: ${response.data.message}`);
            return response.data.task_id;
        } catch (error) {
            console.log(`❌ 分析開始エラー: ${error.response?.data?.detail || error.message}`);
            return null;
        }
    }

    async getStatus(taskId) {
        try {
            const response = await axios.get(`${this.baseUrl}/analysis/sed/${taskId}`);
            return response.data;
        } catch (error) {
            if (error.response?.status === 404) {
                console.log(`❌ タスクが見つかりません: ${taskId}`);
            } else {
                console.log(`❌ 状況取得エラー: ${error.message}`);
            }
            return null;
        }
    }

    async waitForCompletion(taskId, maxWait = 600) {
        console.log(`⏳ 分析完了を待機中... (最大${maxWait}秒)`);
        
        const startTime = Date.now();
        while (true) {
            const status = await this.getStatus(taskId);
            if (!status) return null;

            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            console.log(`📊 進捗: ${status.progress}% - ${status.message} (${elapsed}秒経過)`);

            if (status.status === 'completed') {
                console.log('🎉 分析完了!');
                return status;
            } else if (status.status === 'failed') {
                console.log(`❌ 分析失敗: ${status.error || '不明なエラー'}`);
                return status;
            }

            if (elapsed >= maxWait) {
                console.log('⏰ タイムアウト: 分析が時間内に完了しませんでした');
                return null;
            }

            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }

    async runFullAnalysis(userId, date) {
        console.log(`🚀 SED分析開始: ${userId} / ${date}`);

        // ヘルスチェック
        if (!await this.healthCheck()) {
            console.log('❌ APIサーバーが応答しません');
            return null;
        }

        // 分析開始
        const taskId = await this.startAnalysis(userId, date);
        if (!taskId) return null;

        // 完了まで待機
        const result = await this.waitForCompletion(taskId);
        if (!result) return null;

        // 結果処理
        if (result.status === 'completed' && result.result) {
            const { analysis, upload, total_events, output_path } = result.result;
            
            console.log('\n📊 分析結果:');
            console.log(`  📁 出力ファイル: ${output_path}`);
            console.log(`  🎵 総イベント数: ${total_events}`);
            console.log(`  ☁️ アップロード: 成功 ${upload.success}, 失敗 ${upload.failed}`);
            
            if (analysis.summary_ranking) {
                console.log('\n🏆 上位音響イベント:');
                analysis.summary_ranking.slice(0, 5).forEach((item, i) => {
                    console.log(`  ${i + 1}. ${item.event}: ${item.count}回`);
                });
            }
        }

        return result;
    }
}

// 使用例
async function main() {
    const client = new SEDAnalysisClient();
    
    // 単体分析実行
    await client.runFullAnalysis('device123', '2025-06-21');
    
    // 複数日分析実行
    const dates = ['2025-06-20', '2025-06-21', '2025-06-22'];
    for (const date of dates) {
        console.log('\n' + '='.repeat(50));
        await client.runFullAnalysis('device123', date);
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

main().catch(console.error);
```

## 📊 データフォーマット

### 分析結果

**出力ファイルパス:**
```
/Users/kaya.matsumoto/data/data_accounts/{device_id}/{YYYY-MM-DD}/sed-summary/result.json
```

**JSON構造:**
```json
{
  "summary_ranking": [
    {"event": "Speech", "count": 84},
    {"event": "Explosion", "count": 18},
    {"event": "Crumpling, crinkling", "count": 18},
    {"event": "Fire", "count": 18},
    {"event": "Crackle", "count": 18},
    {"event": "other", "count": 144}
  ],
  "time_blocks": {
    "00-00": ["Speech 84回", "Explosion 18回", "Crumpling, crinkling 18回", "Fire 18回", "Crackle 18回", "その他多数"],
    "00-30": ["データなし"], 
    "01-00": ["データなし"],
    "01-30": ["データなし"]
  }
}
```

### 音響イベントタイプ

**主要なイベント例:**
- **Speech**: 音声・会話
- **Explosion**: 爆発音
- **Crumpling, crinkling**: くしゃくしゃ音、包装紙を丸める音
- **Fire**: 火の音、燃える音
- **Crackle**: パチパチ音、薪が燃える音
- **Fireworks**: 花火の音
- **Silence**: 無音・静寂
- **Inside, small room**: 小さな部屋の室内音
- **Hands**: 手の動作音
- **other**: その他（トップ5以外の集約）

**その他検出される音響イベント:**
- Crack, Slap/smack, Tap, Chopping, Clapping, Percussion, Wood block, Finger snapping, Door, Tearing, Breaking, Breathing, Snoring, Ping, Cap gun, Chop, Scissors, Shuffling cards, Wood, Crushing, Mechanisms, Clip-clop など

## 🏗️ システム構成と依存関係

### 📋 プログラム間の依存関係

```
┌─────────────────────────────────────┐
│          api_server.py              │ ← メインAPIサーバー
│       (FastAPIアプリケーション)        │
└─────────────────────────────────────┘
              │
              ├─ 必須依存 ─→ ┌─────────────────────────────────────┐
              │              │       sed_aggregator.py             │
              │              │   データ収集・集計モジュール            │
              │              │   (単体実行も可能)                   │
              │              └─────────────────────────────────────┘
              │
              └─ 必須依存 ─→ ┌─────────────────────────────────────┐
                             │     upload_sed_summary.py           │
                             │   アップロードモジュール               │
                             │   (単体実行も可能)                   │
                             └─────────────────────────────────────┘

┌─────────────────────────────────────┐
│        example_usage.py             │ ← クライアント使用例
│     (api_server.pyに依存)           │   (独立したファイル)
└─────────────────────────────────────┘
```

### 🔗 **重要**: APIサーバーの動作に必要なファイル

`api_server.py`を実行するためには、以下のファイルが**必須**です：

```python
# api_server.py 内でのインポート
from sed_aggregator import SEDAggregator
from upload_sed_summary import SEDSummaryUploader
```

⚠️ **これらのファイルがないとAPIサーバーは起動できません**

### 📁 各ファイルの詳細機能

#### 🌐 **api_server.py** (メインアプリケーション)
- **役割**: FastAPIベースのREST APIサーバー
- **機能**: 
  - バックグラウンドタスク管理
  - 非同期処理とタスク状況監視
  - 他の2つのモジュールを統合して実行
- **依存関係**: `sed_aggregator.py` + `upload_sed_summary.py` **必須**
- **実行**: `python api_server.py`

#### 📊 **sed_aggregator.py** (データ処理モジュール)
- **役割**: SED データ収集・集計
- **機能**:
  - 48個の30分スロットファイルを並列取得
  - 音響イベントの抽出・集計
  - トップ5ランキング + その他の生成
- **依存関係**: 独立（外部ライブラリのみ）
- **実行**: 
  - API経由: `api_server.py`から自動実行
  - 単体実行: `python sed_aggregator.py device123 2025-06-21`

#### ☁️ **upload_sed_summary.py** (アップロードモジュール)
- **役割**: 分析結果のクラウドストレージアップロード
- **機能**:
  - 成功・失敗の詳細レポート
  - 特定ファイル or 全ファイルのアップロード
- **依存関係**: 独立（外部ライブラリのみ）
- **実行**:
  - API経由: `api_server.py`から自動実行
  - 単体実行: `python upload_sed_summary.py --user-id device123 --date 2025-06-21`

#### 💡 **example_usage.py** (クライアント使用例)
- **役割**: APIクライアントの実装例
- **機能**: 分析開始から完了までの全フロー
- **依存関係**: 実行中の`api_server.py`（REST API呼び出し）
- **実行**: `python example_usage.py`

### 🚀 実行パターン

#### パターン1: API経由での統合実行（推奨）
```bash
# 1. APIサーバー起動（3ファイル必要）
python api_server.py

# 2. REST API経由で実行
curl -X POST "http://localhost:8010/analysis/sed" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device123", "date": "2025-06-21"}'
```

#### パターン2: 個別モジュールの直接実行
```bash
# データ収集・集計のみ
python sed_aggregator.py device123 2025-06-21

# アップロードのみ
python upload_sed_summary.py --user-id device123 --date 2025-06-21

# 全ファイルのアップロード
python upload_sed_summary.py
```

### ⚠️ トラブルシューティング

**APIサーバー起動エラー**
```
ModuleNotFoundError: No module named 'sed_aggregator'
```
→ `sed_aggregator.py`ファイルが同じディレクトリに存在することを確認

```
ModuleNotFoundError: No module named 'upload_sed_summary'  
```
→ `upload_sed_summary.py`ファイルが同じディレクトリに存在することを確認

## 🔧 開発・デバッグ

### ログ出力
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 詳細ログ例
```
INFO:__main__:SED分析開始: task_id=abe82747-bbca-4feb-9f5b-8103128c7580, device_id=device123, date=2025-06-21
データ取得開始: device_id=device123, date=2025-06-21
取得完了: 00-00
ファイルが存在しません: https://api.hey-watch.me/status/device123/2025-06-21/sed/01-00.json
ファイルが存在しません: https://api.hey-watch.me/status/device123/2025-06-21/sed/02-00.json
データ取得完了: 1/48 ファイル
データ集計開始...
集計完了: 総イベント数 300
結果保存完了: /Users/kaya.matsumoto/data/data_accounts/device123/2025-06-21/sed-summary/result.json
INFO:__main__:SED分析完了: task_id=abe82747-bbca-4feb-9f5b-8103128c7580
```

## 🚀 本番デプロイ

### Docker化
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8010

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8010"]
```

### 環境変数
```bash
SED_API_BASE_URL=https://api.hey-watch.me/status
UPLOAD_API_URL=https://api.hey-watch.me/upload/analysis/sed-summary
DATA_BASE_PATH=/app/data
VERIFY_SSL=false  # SSL証明書の検証（true/false、デフォルト: false）
```

## ⚠️ エラーハンドリング

### よくあるエラー

**404 - タスクが見つかりません**
```json
{"detail": "タスクが見つかりません"}
```

**400 - 日付形式エラー**
```json
{"detail": "日付はYYYY-MM-DD形式で指定してください"}
```

**SSL証明書検証エラー**
```
SSLCertVerificationError: certificate verify failed: unable to get local issuer certificate
```
→ 解決方法: 環境変数 `VERIFY_SSL=false` を設定してSSL検証を無効化

**500 - 内部エラー**
```json
{
  "status": "failed",
  "message": "分析中にエラーが発生しました",
  "error": "詳細なエラーメッセージ"
}
```

### 正常な動作
- **404エラー**: 該当スロットのファイルが存在しない場合はスキップ（通常の動作）
- **空ファイル**: 無音期間など、内容が空の場合はスキップ  
- **タイムアウト**: 30秒でタイムアウト、該当スロットをスキップ
- **JSON解析エラー**: 不正な形式のファイルはスキップ
- **データが少ない場合**: 48スロット中1つしかデータがない場合でも正常に処理される
- **SSL証明書検証**: デフォルトで無効化され、ダッシュボード環境での接続問題を回避

## 📞 サポート

**API仕様の詳細:**
- OpenAPI/Swagger UI: `http://localhost:8010/docs`
- ReDoc: `http://localhost:8010/redoc`

**開発者向けサポート:**
- 非同期処理の実装ガイド
- エラーハンドリングベストプラクティス
- パフォーマンス最適化手法
