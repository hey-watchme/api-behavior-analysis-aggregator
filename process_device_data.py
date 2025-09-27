#!/usr/bin/env python3
"""
特定デバイスのデータ処理スクリプト
"""

import asyncio
import os
from datetime import datetime
from sed_aggregator import SEDAggregator
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

async def process_device_data():
    """指定されたデバイスのデータを処理"""
    
    # パラメータ設定
    device_id = "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93"
    date = "2025-09-26"
    
    print("=" * 60)
    print("📊 SED集計処理実行")
    print("=" * 60)
    print(f"Device ID: {device_id}")
    print(f"Date: {date}")
    print()
    
    # 集計実行
    aggregator = SEDAggregator()
    
    print("処理を開始します...")
    print("-" * 40)
    
    # 日本語翻訳ありで処理
    result = await aggregator.run(device_id, date, translate=True)
    
    if result["success"]:
        print("\n✅ 処理成功！")
        
        if "result" in result:
            summary = result["result"]["summary_ranking"]
            
            print(f"\n📊 生活音ランキング（全{len(summary)}件）:")
            print("-" * 40)
            
            # 優先イベントを先に表示
            priority_events = [e for e in summary if e.get("priority", False)]
            regular_events = [e for e in summary if not e.get("priority", False)]
            
            if priority_events:
                print("\n⭐ 優先イベント（健康モニタリング）:")
                for item in priority_events:
                    category_label = {
                        "biometric": "生体反応",
                        "voice": "声・会話",
                        "daily_life": "生活音"
                    }.get(item.get("category", "other"), "その他")
                    print(f"   - {item['event']}: {item['count']}回 [{category_label}]")
            
            if regular_events:
                print(f"\n📈 通常ランキング（上位10件）:")
                for i, item in enumerate(regular_events[:10], 1):
                    print(f"   {i}. {item['event']}: {item['count']}回")
            
            # 時間帯別のサマリー
            time_blocks = result["result"]["time_blocks"]
            active_slots = [slot for slot, events in time_blocks.items() 
                          if events is not None and len(events) > 0]
            
            print(f"\n⏰ 時間帯別活動:")
            print(f"   アクティブな時間帯: {len(active_slots)}/48 スロット")
            
            if active_slots:
                print(f"   最も活動的な時間帯:")
                # 各スロットのイベント数を計算
                slot_activity = []
                for slot in active_slots[:5]:
                    events = time_blocks[slot]
                    total_count = sum(e.get("count", 0) for e in events)
                    slot_activity.append((slot, total_count))
                
                slot_activity.sort(key=lambda x: x[1], reverse=True)
                
                for slot, count in slot_activity[:5]:
                    hour = slot.replace("-", ":")
                    print(f"     - {hour}: {count}イベント")
    else:
        print(f"\n❌ 処理失敗: {result.get('message', '不明なエラー')}")
        
        if result.get("reason") == "no_data":
            print("\n💡 ヒント: この日付にはデータが存在しない可能性があります。")
            print("   behavior_yamnetテーブルにデータがあるか確認してください。")
    
    print()
    print("=" * 60)
    print("処理完了")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(process_device_data())