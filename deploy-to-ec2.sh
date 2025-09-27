#!/bin/bash

# デプロイスクリプト for SED Aggregator API
# EC2サーバーに.envファイルと設定をデプロイ

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
EC2_HOST="3.24.16.82"
EC2_USER="ubuntu"
EC2_KEY="~/watchme-key.pem"
REMOTE_PATH="/home/ubuntu/api-sed-aggregator"

echo -e "${GREEN}🚀 SED Aggregator API - EC2デプロイ開始${NC}"
echo "=================================="

# 1. .envファイルの存在確認
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .envファイルが見つかりません${NC}"
    exit 1
fi

echo -e "${YELLOW}📝 設定を確認中...${NC}"
echo "  EC2ホスト: $EC2_HOST"
echo "  リモートパス: $REMOTE_PATH"

# 2. .envファイルをEC2サーバーにコピー
echo -e "\n${YELLOW}📤 .envファイルをEC2サーバーにコピー中...${NC}"
scp -i $EC2_KEY .env $EC2_USER@$EC2_HOST:$REMOTE_PATH/.env
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ .envファイルのコピーに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ .envファイルのコピー成功${NC}"

# 3. docker-compose.prod.ymlをEC2サーバーにコピー
echo -e "\n${YELLOW}📤 docker-compose.prod.ymlをEC2サーバーにコピー中...${NC}"
scp -i $EC2_KEY docker-compose.prod.yml $EC2_USER@$EC2_HOST:$REMOTE_PATH/docker-compose.prod.yml
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ docker-compose.prod.ymlのコピーに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ docker-compose.prod.ymlのコピー成功${NC}"

# 4. EC2サーバーでコンテナを再起動
echo -e "\n${YELLOW}🔄 EC2サーバーでコンテナを再起動中...${NC}"
ssh -i $EC2_KEY $EC2_USER@$EC2_HOST << EOF
    set -e
    cd $REMOTE_PATH
    
    echo "📦 最新のイメージをプル..."
    docker pull 754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-api-behavior-aggregator:latest
    
    echo "🛑 既存のコンテナを停止..."
    docker-compose -f docker-compose.prod.yml down || true
    
    echo "🚀 新しいコンテナを起動..."
    docker-compose -f docker-compose.prod.yml up -d
    
    echo "⏳ ヘルスチェックを待機中..."
    sleep 5
    
    echo "🩺 ヘルスチェック..."
    curl -s http://localhost:8010/health | jq '.' || echo "API is not responding"
    
    echo "📝 コンテナステータス:"
    docker ps | grep api-sed-aggregator || echo "コンテナが見つかりません"
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ コンテナの再起動に失敗しました${NC}"
    exit 1
fi

echo -e "${GREEN}✅ コンテナの再起動成功${NC}"

# 5. 動作確認
echo -e "\n${YELLOW}🔍 API動作確認中...${NC}"
API_HEALTH=$(curl -s http://$EC2_HOST:8010/health 2>/dev/null | jq -r '.status' 2>/dev/null)
if [ "$API_HEALTH" == "healthy" ]; then
    echo -e "${GREEN}✅ APIは正常に動作しています${NC}"
else
    echo -e "${YELLOW}⚠️  APIのレスポンスを確認してください${NC}"
    curl -s http://$EC2_HOST:8010/health | jq '.' 2>/dev/null || echo "APIから応答がありません"
fi

# 6. ログの確認
echo -e "\n${YELLOW}📋 最新のコンテナログ:${NC}"
ssh -i $EC2_KEY $EC2_USER@$EC2_HOST "cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml logs --tail=20 api"

echo -e "\n${GREEN}=================================="
echo -e "🎉 デプロイが完了しました！"
echo -e "==================================\n"
echo -e "API URL: ${BLUE}http://$EC2_HOST:8010${NC}"
echo -e "Health Check: ${BLUE}http://$EC2_HOST:8010/health${NC}"
echo -e "Swagger Docs: ${BLUE}http://$EC2_HOST:8010/docs${NC}"
echo -e "\n${YELLOW}次のステップ:${NC}"
echo -e "1. タスク一覧を確認: curl -s http://$EC2_HOST:8010/analysis/sed | jq '.'"
echo -e "2. 必要に応じて手動でテスト実行"