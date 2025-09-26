#!/bin/bash
# SED Aggregator API - 本番環境デプロイスクリプト

set -e  # エラーが発生したら即座に終了

echo "🚀 Starting SED Aggregator API deployment..."

# 環境変数の設定
export AWS_REGION="ap-southeast-2"
export ECR_REGISTRY="754724220380.dkr.ecr.ap-southeast-2.amazonaws.com"
export ECR_REPOSITORY="watchme-api-sed-aggregator"
export CONTAINER_NAME="api-sed-aggregator"

# ECRログイン
echo "🔐 Logging into Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# 最新のイメージをプル
echo "📦 Pulling latest image from ECR..."
docker pull ${ECR_REGISTRY}/${ECR_REPOSITORY}:latest

# 既存のコンテナを停止・削除（存在する場合）
echo "🛑 Stopping existing container (if any)..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# 環境変数ファイルの確認
if [ ! -f /home/ubuntu/.env ]; then
    echo "⚠️ Warning: .env file not found at /home/ubuntu/.env"
    echo "Creating .env file from example..."
    # 必要に応じて.envファイルを作成
    cat > /home/ubuntu/.env << EOF
# Supabase設定
SUPABASE_URL=https://qvtlwotzuzbavrzqhyvt.supabase.co
SUPABASE_KEY=your-supabase-key-here
EOF
    echo "⚠️ Please update /home/ubuntu/.env with actual Supabase credentials"
fi

# 新しいコンテナを起動
echo "🚀 Starting new container..."
docker run -d \
  --name ${CONTAINER_NAME} \
  --restart unless-stopped \
  -p 8010:8010 \
  --env-file /home/ubuntu/.env \
  ${ECR_REGISTRY}/${ECR_REPOSITORY}:latest

# コンテナが正常に起動したか確認
echo "⏳ Waiting for container to start..."
sleep 5

# コンテナの状態を確認
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo "✅ Container is running!"
    
    # ヘルスチェック
    echo "🏥 Performing health check..."
    sleep 3
    if curl -f http://localhost:8010/health > /dev/null 2>&1; then
        echo "✅ Health check passed!"
    else
        echo "⚠️ Health check failed, but container is running"
    fi
    
    # コンテナログの最後の10行を表示
    echo "📋 Recent container logs:"
    docker logs --tail 10 ${CONTAINER_NAME}
else
    echo "❌ Container failed to start!"
    echo "📋 Container logs:"
    docker logs ${CONTAINER_NAME}
    exit 1
fi

# 古いイメージのクリーンアップ
echo "🧹 Cleaning up old images..."
docker image prune -f

echo "✅ Deployment completed successfully!"
echo "🌐 API is available at: https://api.hey-watch.me/behavior-aggregator/"