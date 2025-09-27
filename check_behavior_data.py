#!/usr/bin/env python3
"""behavior_yamnetテーブルのデータ形式を確認するスクリプト"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
from datetime import datetime, date

# .envファイルから環境変数を読み込み
load_dotenv()

# Supabaseクライアントの初期化
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

def check_behavior_data():
    """behavior_yamnetテーブルのデータ形式を確認"""
    
    # テスト用のデバイスIDと日付
    device_id = "d067d407-cf73-4174-a9c1-d91fb60d64d0"
    test_date = "2025-09-27"
    
    print(f"📊 データ形式確認")
    print(f"Device ID: {device_id}")
    print(f"Date: {test_date}")
    print("=" * 80)
    
    try:
        # データを取得
        response = supabase.table('behavior_yamnet').select('*').eq(
            'device_id', device_id
        ).eq(
            'date', test_date
        ).limit(5).execute()
        
        if not response.data:
            print("❌ データが見つかりません")
            
            # 他の日付も試す
            test_date2 = "2025-09-26"
            print(f"\n別の日付で試します: {test_date2}")
            response = supabase.table('behavior_yamnet').select('*').eq(
                'device_id', device_id
            ).eq(
                'date', test_date2
            ).limit(5).execute()
        
        if response.data:
            print(f"✅ {len(response.data)}件のデータを取得しました")
            
            for i, row in enumerate(response.data[:3]):  # 最初の3件のみ詳細表示
                print(f"\n--- Record {i+1} ---")
                print(f"Time block: {row['time_block']}")
                print(f"Events type: {type(row['events'])}")
                
                events = row['events']
                if events:
                    if isinstance(events, str):
                        events = json.loads(events)
                    
                    print(f"Events structure:")
                    
                    # eventsの構造を分析
                    if isinstance(events, list) and len(events) > 0:
                        first_event = events[0]
                        print(f"  - First item type: {type(first_event)}")
                        print(f"  - First item keys: {first_event.keys() if isinstance(first_event, dict) else 'N/A'}")
                        
                        # 最初の3個のイベントを表示
                        for j, event in enumerate(events[:3]):
                            print(f"  - Event {j+1}: {json.dumps(event, ensure_ascii=False)[:200]}")
                            
                        # 形式を判定
                        if isinstance(first_event, dict):
                            if 'time' in first_event and 'events' in first_event:
                                print("  📍 形式: 新形式 (AST) - {time: x, events: [...]}")
                                # 実際のイベントデータを表示
                                if 'events' in first_event and isinstance(first_event['events'], list):
                                    actual_events = first_event['events']
                                    print(f"  📍 実際のイベント数: {len(actual_events)}")
                                    if actual_events:
                                        print(f"  📍 イベントの例: {actual_events[0]}")
                            elif 'label' in first_event and 'prob' in first_event:
                                print("  📍 形式: 旧形式 (YAMNet) - {label: xxx, prob: x}")
                            else:
                                print(f"  📍 形式: 不明 - keys: {list(first_event.keys())}")
                else:
                    print("  ⚠️ Events is empty or None")
        
        else:
            print("❌ どちらの日付でもデータが見つかりません")
            
            # 最新のデータを確認
            print("\n最新のデータを確認中...")
            latest_response = supabase.table('behavior_yamnet').select('*').order(
                'date', desc=True
            ).limit(5).execute()
            
            if latest_response.data:
                print(f"✅ 最新の{len(latest_response.data)}件のデータ:")
                for row in latest_response.data:
                    print(f"  - {row['device_id']}: {row['date']} - {row['time_block']}")
            else:
                print("❌ テーブルにデータがありません")
                
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    check_behavior_data()