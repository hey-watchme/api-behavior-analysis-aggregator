#!/usr/bin/env python3
"""
Supabase版 SED Aggregatorのテストスクリプト
"""

import asyncio
from sed_aggregator import SEDAggregator
from datetime import datetime

async def test_aggregator():
    """SEDAggregatorのテスト"""
    
    # テストパラメータ
    device_id = "d067d407-cf73-4174-a9c1-d91fb60d64d0"
    date = "2025-07-07"  # データが存在する日付
    
    print("🧪 Supabase版 SED Aggregatorテスト開始")
    print(f"📋 パラメータ: device_id={device_id}, date={date}")
    print("-" * 60)
    
    try:
        # Aggregatorインスタンス作成
        aggregator = SEDAggregator()
        
        # データ取得テスト
        print("\n📊 Supabaseからデータ取得中...")
        slot_data = await aggregator.fetch_all_data(device_id, date)
        
        if slot_data:
            print(f"✅ データ取得成功: {len(slot_data)} スロット")
            
            # 最初の3スロットのデータを表示
            count = 0
            for time_block, events in sorted(slot_data.items())[:3]:
                print(f"\n🕐 スロット: {time_block}")
                print(f"   イベント数: {len(events)}")
                if events:
                    print(f"   サンプル: {events[0] if events else 'なし'}")
                count += 1
            
            # 集計処理テスト
            print("\n📊 集計処理実行中...")
            result = aggregator.aggregate_data(slot_data)
            
            print("\n📈 集計結果:")
            print("  サマリーランキング:")
            for item in result['summary_ranking'][:5]:
                print(f"    - {item['event']}: {item['count']}回")
            
            # フルの処理実行
            print("\n🚀 フル処理実行中...")
            output_path = await aggregator.run(device_id, date)
            
            if output_path:
                print(f"\n✅ 処理完了!")
                print(f"📄 出力ファイル: {output_path}")
            else:
                print("\n❌ 処理失敗")
                
        else:
            print("⚠️ データが見つかりません")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Supabase版 SED Aggregator テスト")
    print("=" * 70)
    
    asyncio.run(test_aggregator())
    
    print("\n" + "=" * 70)
    print("🏁 テスト完了")
    print("=" * 70)