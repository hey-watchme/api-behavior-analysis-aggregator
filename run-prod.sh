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

# 既存のコンテナを停止（Docker Composeを使用）
echo "🛑 Stopping existing container (if any)..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# 環境変数ファイルの確認（カレントディレクトリ）
if [ ! -f .env ]; then
    echo "⚠️ Warning: .env file not found in current directory"
    echo "ℹ️  Note: .env file should be created by GitHub Actions or manually"
    echo "   If running manually, create .env with:"
    echo "   SUPABASE_URL=<your-url>"
    echo "   SUPABASE_KEY=<your-key>"
    exit 1
else
    echo "✅ .env file found in current directory"
    echo "📋 .env file contains $(wc -l < .env) lines"
fi

# 新しいコンテナを起動（Docker Composeを使用）
echo "🚀 Starting new container with docker-compose..."
docker-compose -f docker-compose.prod.yml up -d

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