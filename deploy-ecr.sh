#!/bin/bash

# ECR設定
ECR_REGISTRY="754724220380.dkr.ecr.ap-southeast-2.amazonaws.com"
ECR_REPOSITORY="watchme-api-sed-aggregator"
IMAGE_TAG="latest"
REGION="ap-southeast-2"

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Behavior Aggregator API - ECRデプロイ開始${NC}"
echo "=================================="

# 環境変数チェック
echo -e "\n${YELLOW}🔍 環境設定を確認中...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .envファイルが見つかりません${NC}"
    echo -e "${YELLOW}📝 .env.exampleを参考に.envファイルを作成してください${NC}"
    exit 1
fi

# 環境変数の値をチェック（プレースホルダーのままでないか）
source .env
if [ "$SUPABASE_KEY" = "your-supabase-key-here" ] || [ -z "$SUPABASE_KEY" ]; then
    echo -e "${RED}❌ SUPABASE_KEYが正しく設定されていません${NC}"
    echo -e "${YELLOW}📝 .envファイルのSUPABASE_KEYを実際の値に更新してください${NC}"
    exit 1
fi

if [ -z "$SUPABASE_URL" ]; then
    echo -e "${RED}❌ SUPABASE_URLが設定されていません${NC}"
    echo -e "${YELLOW}📝 .envファイルのSUPABASE_URLを設定してください${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 環境変数の確認完了${NC}"

# 1. ECRにログイン
echo -e "\n${YELLOW}📝 ECRにログイン中...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ECRログインに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ECRログイン成功${NC}"

# 2. Dockerイメージのビルド
echo -e "\n${YELLOW}🔨 Dockerイメージをビルド中...${NC}"
docker build -f Dockerfile.prod -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Dockerビルドに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Dockerビルド成功${NC}"

# 3. イメージにタグ付け
echo -e "\n${YELLOW}🏷️  イメージにタグ付け中...${NC}"
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ タグ付けに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ タグ付け成功${NC}"

# 4. ECRにプッシュ
echo -e "\n${YELLOW}📤 ECRにイメージをプッシュ中...${NC}"
docker push ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ECRプッシュに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ECRプッシュ成功${NC}"

# 5. デプロイ完了
echo -e "\n${GREEN}=================================="
echo -e "🎉 デプロイが正常に完了しました！"
echo -e "==================================\n"
echo -e "イメージURI: ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
echo -e "\n次のステップ:"
echo -e "1. EC2サーバーにSSH接続"
echo -e "   ${YELLOW}ssh -i ~/watchme-key.pem ubuntu@3.24.16.82${NC}"
echo -e "2. systemdサービスを更新（docker-compose.prod.ymlでECRイメージを使用）"
echo -e "   ${YELLOW}cd /home/ubuntu/api-sed-aggregator${NC}"
echo -e "   ${YELLOW}# docker-compose.prod.ymlを編集してECRイメージを指定${NC}"
echo -e "3. サービスを再起動"
echo -e "   ${YELLOW}sudo systemctl restart api-sed-aggregator.service${NC}"