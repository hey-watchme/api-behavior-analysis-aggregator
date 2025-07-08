#!/usr/bin/env python3
"""
SED（Sound Event Detection）データ集計ツール

Supabaseのbehavior_yamnetテーブルから音響イベント検出データを収集し、
日次集計結果をローカルに保存する。
"""

import asyncio
import json
import os
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse
from supabase import create_client, Client
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()


class SEDAggregator:
    """SED データ集計クラス"""
    
    def __init__(self):
        # Supabaseクライアントの初期化
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URLおよびSUPABASE_KEYが設定されていません")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.time_slots = self._generate_time_slots()
        print(f"✅ Supabase接続設定完了")
    
    def _generate_time_slots(self) -> List[str]:
        """30分スロットのリストを生成（00-00 から 23-30 まで）"""
        slots = []
        for hour in range(24):
            for minute in [0, 30]:
                slots.append(f"{hour:02d}-{minute:02d}")
        return slots
    
    async def fetch_all_data(self, device_id: str, date: str) -> Dict[str, List[Dict]]:
        """指定日の全SEDデータをSupabaseから取得"""
        print(f"📊 Supabaseからデータ取得開始: device_id={device_id}, date={date}")
        
        try:
            # Supabaseからデータを取得
            response = self.supabase.table('behavior_yamnet').select('*').eq(
                'device_id', device_id
            ).eq(
                'date', date
            ).execute()
            
            # 結果をtime_blockごとに整理
            results = {}
            for row in response.data:
                time_block = row['time_block']
                events = row['events']  # jsonb型なのでそのまま辞書として扱える
                results[time_block] = events
            
            print(f"✅ データ取得完了: {len(results)}/{len(self.time_slots)} スロット")
            return results
            
        except Exception as e:
            print(f"❌ Supabaseからのデータ取得エラー: {e}")
            return {}
    
    def _extract_events_from_supabase(self, events_data: List[Dict]) -> List[str]:
        """Supabaseのeventsカラムから音響イベントラベルを抽出"""
        events = []
        
        # events_dataは[{"label": "Speech", "prob": 0.98}, ...]の形式
        for event in events_data:
            if isinstance(event, dict) and 'label' in event:
                events.append(event['label'])
        
        return events
    
    def _create_summary_ranking(self, all_events: List[str]) -> List[Dict[str, int]]:
        """全体イベントからトップ5ランキングを作成"""
        counter = Counter(all_events)
        top_5 = counter.most_common(5)
        
        ranking = []
        other_count = 0
        
        for event, count in counter.items():
            if (event, count) in top_5:
                ranking.append({"event": event, "count": count})
            else:
                other_count += count
        
        if other_count > 0:
            ranking.append({"event": "other", "count": other_count})
        
        # ランキングを出現回数でソート
        ranking.sort(key=lambda x: x['count'], reverse=True)
        
        return ranking
    
    def _create_time_blocks(self, slot_data: Dict[str, List[Dict]]) -> Dict[str, Optional[List[Dict[str, Any]]]]:
        """スロット別のイベント集計を構造化形式で作成"""
        time_blocks = {}
        
        for slot in self.time_slots:
            if slot in slot_data:
                events = self._extract_events_from_supabase(slot_data[slot])
                if events:
                    counter = Counter(events)
                    # イベントを構造化形式で表現
                    event_list = []
                    for event, count in counter.most_common():
                        event_list.append({"event": event, "count": count})
                    time_blocks[slot] = event_list
                else:
                    # データは存在するがイベントが空の場合
                    time_blocks[slot] = []
            else:
                # データが存在しない場合はnull
                time_blocks[slot] = None
        
        return time_blocks
    
    def aggregate_data(self, slot_data: Dict[str, List[Dict]]) -> Dict:
        """収集したデータを集計して結果形式を生成"""
        print("📊 データ集計開始...")
        
        # 全イベントを収集
        all_events = []
        for events_data in slot_data.values():
            events = self._extract_events_from_supabase(events_data)
            all_events.extend(events)
        
        # summary_ranking作成
        summary_ranking = self._create_summary_ranking(all_events)
        
        # time_blocks作成
        time_blocks = self._create_time_blocks(slot_data)
        
        result = {
            "summary_ranking": summary_ranking,
            "time_blocks": time_blocks
        }
        
        print(f"✅ 集計完了: 総イベント数 {len(all_events)}")
        return result
    
    async def save_to_supabase(self, result: Dict, device_id: str, date: str) -> bool:
        """結果をSupabaseのbehavior_summaryテーブルに保存"""
        try:
            # Supabaseにデータを保存（UPSERT）
            response = self.supabase.table('behavior_summary').upsert({
                'device_id': device_id,
                'date': date,
                'summary_ranking': result['summary_ranking'],
                'time_blocks': result['time_blocks']
            }).execute()
            
            print(f"💾 Supabase保存完了: behavior_summary テーブル")
            print(f"   device_id: {device_id}, date: {date}")
            return True
            
        except Exception as e:
            print(f"❌ Supabase保存エラー: {e}")
            return False
    
    async def run(self, device_id: str, date: str) -> bool:
        """メイン処理実行"""
        print(f"🚀 SED集計処理開始: {device_id}, {date}")
        
        # Supabaseからデータ取得
        slot_data = await self.fetch_all_data(device_id, date)
        
        if not slot_data:
            print("⚠️ 取得できたデータがありません")
            return False
        
        # データ集計
        result = self.aggregate_data(slot_data)
        
        # Supabaseに保存
        success = await self.save_to_supabase(result, device_id, date)
        
        if success:
            print("🎉 SED集計処理完了")
        
        return success


async def main():
    """コマンドライン実行用メイン関数"""
    parser = argparse.ArgumentParser(description="SED データ集計ツール (Supabase版)")
    parser.add_argument("device_id", help="デバイスID（例: d067d407-cf73-4174-a9c1-d91fb60d64d0）")
    parser.add_argument("date", help="対象日付（YYYY-MM-DD形式）")
    
    args = parser.parse_args()
    
    # 日付形式検証
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("❌ エラー: 日付はYYYY-MM-DD形式で指定してください")
        return
    
    # 集計実行
    aggregator = SEDAggregator()
    success = await aggregator.run(args.device_id, args.date)
    
    if success:
        print(f"\n✅ 処理完了")
        print(f"💾 データはSupabaseのbehavior_summaryテーブルに保存されました")
    else:
        print("\n❌ 処理失敗")


if __name__ == "__main__":
    asyncio.run(main())