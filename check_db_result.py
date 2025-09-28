#!/usr/bin/env python3
"""
データベースに保存された結果を確認するスクリプト
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import json

# 環境変数を読み込み
load_dotenv()

def check_database_result():
    """データベースの結果を確認"""
    
    # Supabase接続
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    # データ取得
    device_id = "d067d407-cf73-4174-a9c1-d91fb60d64d0"
    date = "2025-09-28"
    
    print("=" * 60)
    print("データベース保存結果確認")
    print("=" * 60)
    print(f"Device ID: {device_id}")
    print(f"Date: {date}")
    print()
    
    # behavior_summaryテーブルから取得
    response = supabase.table('behavior_summary').select('*').eq(
        'device_id', device_id
    ).eq(
        'date', date
    ).execute()
    
    if response.data:
        data = response.data[0]
        
        print("📊 Summary Ranking:")
        print("-" * 40)
        summary = data['summary_ranking']
        
        if isinstance(summary, list):
            if len(summary) > 0:
                for i, item in enumerate(summary[:10], 1):
                    if isinstance(item, dict):
                        event = item.get('event', 'Unknown')
                        count = item.get('count', 0)
                        priority = item.get('priority', False)
                        category = item.get('category', 'other')
                        priority_mark = "⭐" if priority else "  "
                        print(f"{priority_mark} {i}. {event} (回数: {count}, カテゴリ: {category})")
                    else:
                        print(f"   {i}. データ形式エラー: {item}")
            else:
                print("   空のリスト")
        else:
            print(f"   データ形式エラー: {type(summary)}")
        
        print()
        print("📈 Time Blocks (サンプル):")
        print("-" * 40)
        time_blocks = data['time_blocks']
        
        # 15-00と13-00のスロットを確認
        for slot in ['15-00', '13-00', '13-30']:
            if slot in time_blocks:
                events = time_blocks[slot]
                if events is not None:
                    if isinstance(events, list) and len(events) > 0:
                        print(f"   {slot}: {events[:3]}...")
                    elif isinstance(events, list) and len(events) == 0:
                        print(f"   {slot}: []（データあるが空）")
                    else:
                        print(f"   {slot}: {events}")
                else:
                    print(f"   {slot}: null（データなし）")
        
        print()
        print("✅ データベースに正常に保存されています")
    else:
        print("❌ データが見つかりません")
    
    print("=" * 60)

if __name__ == "__main__":
    check_database_result()