#!/bin/bash

echo "=== api-sed-aggregator 調査 ==="
echo ""

# 1. ヘルスチェック
echo "1. APIヘルスチェック:"
curl -s https://api.hey-watch.me/behavior-aggregator/health | jq '.' || echo "ヘルスチェック失敗"
echo ""

# 2. 手動でAPIを叩いてテスト
echo "2. 手動でAPI実行テスト:"
TASK_ID=$(curl -s -X POST https://api.hey-watch.me/behavior-aggregator/analysis/sed \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0",
    "date": "2025-09-28"
  }' | jq -r '.task_id')

echo "Task ID: $TASK_ID"
echo ""

# 3. タスクステータス確認（3秒待機）
if [ ! -z "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
  echo "3秒待機中..."
  sleep 3
  echo ""
  echo "3. タスクステータス:"
  curl -s "https://api.hey-watch.me/behavior-aggregator/analysis/sed/$TASK_ID" | jq '.'
else
  echo "タスクIDが取得できませんでした"
fi
echo ""

# 4. EC2の状態確認コマンド（手動実行用）
echo "=== EC2で実行するコマンド ==="
echo "ssh -i ~/watchme-key.pem ubuntu@3.24.16.82"
echo ""
echo "# .envファイル確認"
echo "cat /home/ubuntu/api-sed-aggregator/.env | head -2"
echo ""
echo "# コンテナ状態"
echo "docker ps | grep api-sed-aggregator"
echo ""
echo "# コンテナログ（最新50行）"
echo "docker logs api-sed-aggregator --tail 50"
echo ""
echo "# コンテナ内の環境変数確認"
echo "docker exec api-sed-aggregator env | grep SUPABASE"