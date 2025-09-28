#!/bin/bash

# EC2サーバーの診断スクリプト
echo "🔍 EC2サーバー診断開始..."
echo "=================================="

# 1. 実行中のコンテナ確認
echo -e "\n📦 実行中のコンテナ:"
ssh -o StrictHostKeyChecking=no ubuntu@3.24.16.82 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"'

# 2. 最新のイメージ確認
echo -e "\n🖼️ Dockerイメージ:"
ssh ubuntu@3.24.16.82 'docker images | grep sed-aggregator'

# 3. コンテナログの最後20行
echo -e "\n📋 コンテナログ（最新20行）:"
ssh ubuntu@3.24.16.82 'docker logs api-sed-aggregator --tail 20 2>&1'

# 4. 環境変数の確認（キー名のみ）
echo -e "\n🔐 環境変数（キー名のみ）:"
ssh ubuntu@3.24.16.82 'docker exec api-sed-aggregator env | cut -d= -f1 | grep -E "SUPABASE|AWS" | sort'

# 5. .envファイルの存在確認
echo -e "\n📄 .envファイルの状態:"
ssh ubuntu@3.24.16.82 'ls -la /home/ubuntu/api-sed-aggregator/.env 2>&1'
ssh ubuntu@3.24.16.82 'wc -l /home/ubuntu/api-sed-aggregator/.env 2>&1'

# 6. ヘルスチェック
echo -e "\n❤️ ヘルスチェック:"
curl -s http://3.24.16.82:8010/health || echo "❌ ヘルスチェック失敗"

# 7. APIレスポンス確認
echo -e "\n🌐 APIステータス:"
curl -s http://3.24.16.82:8010/ || echo "❌ API応答なし"

echo -e "\n=================================="
echo "診断完了"