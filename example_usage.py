#!/usr/bin/env python3
"""
SED分析API クライアント使用例

APIサーバーを使用してSED分析を実行する方法を示します。
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class SEDAnalysisClient:
    """SED分析APIクライアント"""
    
    def __init__(self, base_url: str = "http://localhost:8010"):
        self.base_url = base_url
    
    async def start_analysis(self, user_id: str, date: str) -> str:
        """分析を開始してタスクIDを取得"""
        url = f"{self.base_url}/analysis/sed"
        data = {"user_id": user_id, "date": date}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["task_id"]
                else:
                    error = await response.text()
                    raise Exception(f"分析開始エラー: {error}")
    
    async def get_status(self, task_id: str) -> dict:
        """タスク状況を取得"""
        url = f"{self.base_url}/analysis/sed/{task_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    raise Exception(f"状況取得エラー: {error}")
    
    async def wait_for_completion(self, task_id: str, max_wait: int = 600) -> dict:
        """分析完了まで待機"""
        print(f"⏳ 分析完了を待機中... (最大{max_wait}秒)")
        
        for i in range(max_wait):
            status = await self.get_status(task_id)
            
            print(f"📊 進捗: {status['progress']}% - {status['message']}")
            
            if status['status'] == 'completed':
                print("✅ 分析完了!")
                return status
            elif status['status'] == 'failed':
                print(f"❌ 分析失敗: {status.get('error', '不明なエラー')}")
                return status
            
            await asyncio.sleep(1)
        
        raise Exception("タイムアウト: 分析が時間内に完了しませんでした")


async def example_api_usage():
    """API使用例の実行"""
    print("SED分析API クライアント使用例")
    print("=" * 50)
    
    client = SEDAnalysisClient()
    
    # 実行パラメータ
    user_id = "user123"
    date = "2025-01-20"  # 実際の日付に変更してください
    
    print(f"📋 分析パラメータ:")
    print(f"  ユーザーID: {user_id}")
    print(f"  対象日付: {date}")
    print()
    
    try:
        # 1. 分析開始
        print("🚀 分析開始...")
        task_id = await client.start_analysis(user_id, date)
        print(f"   タスクID: {task_id}")
        
        # 2. 完了まで待機
        result = await client.wait_for_completion(task_id)
        
        # 3. 結果表示
        if result['status'] == 'completed' and 'result' in result:
            analysis_data = result['result']['analysis']
            upload_data = result['result']['upload']
            
            print("\n📊 分析結果:")
            print(f"  📁 出力ファイル: {result['result']['output_path']}")
            print(f"  🎵 総イベント数: {result['result']['total_events']}")
            print(f"  ☁️ アップロード: 成功 {upload_data['success']}, 失敗 {upload_data['failed']}")
            
            if analysis_data['summary_ranking']:
                print("\n🏆 上位音響イベント:")
                for i, item in enumerate(analysis_data['summary_ranking'][:5], 1):
                    print(f"  {i}. {item['event']}: {item['count']}回")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")


async def example_health_check():
    """ヘルスチェック例"""
    print("\n🔍 APIヘルスチェック")
    print("-" * 30)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8010/health") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ API稼働中: {result}")
                else:
                    print(f"❌ APIエラー: HTTP {response.status}")
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        print("💡 api_server.pyを起動してください")


if __name__ == "__main__":
    asyncio.run(example_health_check())
    asyncio.run(example_api_usage()) 