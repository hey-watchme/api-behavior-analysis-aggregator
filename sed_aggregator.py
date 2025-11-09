#!/usr/bin/env python3
"""
SED（Sound Event Detection）データ集計ツール

Supabaseのaudio_featuresテーブルから音響イベント検出データを収集し、
日次集計結果をaudio_aggregatorテーブルに保存する。

処理フロー:
1. audio_features.behavior_extractor_resultから生データ取得
2. フィルタリング（不要なイベント除外）
3. 統合（類似イベントをまとめる）
4. time_blocks作成（30分スロット別の集計）
5. summary_ranking作成（time_blocksから1日全体を集計、アプリ側で使用）
6. time_blocksをaudio_aggregator.behavior_aggregator_resultに保存
"""

import asyncio
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

# ==================== 設定 ====================

# 除外するイベントラベルのリスト（最初は空）
EXCLUDED_EVENTS = []

# 音の統合マッピング（最初は空）
SOUND_CONSOLIDATION = {}

# カテゴリー定義（最初は空）
PRIORITY_CATEGORIES = {}


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
            # Supabaseからデータを取得（audio_featuresテーブル）
            response = self.supabase.table('audio_features').select('time_block, behavior_extractor_result').eq(
                'device_id', device_id
            ).eq(
                'date', date
            ).execute()

            # 結果をtime_blockごとに整理
            results = {}
            for row in response.data:
                time_block = row['time_block']
                events = row['behavior_extractor_result']  # jsonb型なのでそのまま辞書として扱える
                if events:  # データが存在する場合のみ追加
                    results[time_block] = events

            print(f"✅ データ取得完了: {len(results)}/{len(self.time_slots)} スロット")
            return results

        except Exception as e:
            print(f"❌ Supabaseからのデータ取得エラー: {e}")
            return {}

    def _extract_events_from_data(self, events_data: List[Dict]) -> List[str]:
        """Supabaseのeventsカラムから音響イベントラベルを抽出

        新形式対応:
        [
          {"time": 0, "events": [{"label": "Speech / 会話・発話", "score": 0.85}, ...]},
          ...
        ]
        """
        events = []

        if not events_data or len(events_data) == 0:
            return events

        # 新形式チェック: {"time": 0.0, "events": [...]}
        for time_block in events_data:
            if isinstance(time_block, dict) and 'events' in time_block:
                for event in time_block['events']:
                    if isinstance(event, dict) and 'label' in event:
                        label = event['label']
                        events.append(label)

        return events

    def _filter_events(self, events: List[str]) -> List[str]:
        """除外リストに基づいてイベントをフィルタリング"""
        if not EXCLUDED_EVENTS:
            return events
        return [e for e in events if e not in EXCLUDED_EVENTS]

    def _consolidate_events(self, events: List[str]) -> List[str]:
        """音の統合マッピングを適用"""
        if not SOUND_CONSOLIDATION:
            return events
        return [SOUND_CONSOLIDATION.get(e, e) for e in events]

    def _get_category(self, event: str) -> str:
        """イベントのカテゴリーを判定（最初は全て "other"）"""
        if not PRIORITY_CATEGORIES:
            return "other"

        for category, events in PRIORITY_CATEGORIES.items():
            if event in events:
                return category
        return "other"

    def _create_time_blocks(self, slot_data: Dict[str, List[Dict]]) -> Dict[str, Optional[List[Dict[str, Any]]]]:
        """スロット別のイベント集計を作成"""
        time_blocks = {}

        for slot in self.time_slots:
            if slot in slot_data:
                # 生イベント抽出
                raw_events = self._extract_events_from_data(slot_data[slot])

                if raw_events:
                    # フィルタリング
                    filtered_events = self._filter_events(raw_events)

                    # 統合
                    consolidated_events = self._consolidate_events(filtered_events)

                    # カウント
                    counter = Counter(consolidated_events)
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

    def _create_summary_ranking(self, time_blocks: Dict[str, Optional[List[Dict]]]) -> List[Dict[str, Any]]:
        """time_blocksから1日全体のランキングを作成"""
        # time_blocksから全イベントを収集
        all_events = []
        for events_list in time_blocks.values():
            if events_list:
                for item in events_list:
                    # item["count"]回分のイベントを追加
                    all_events.extend([item["event"]] * item["count"])

        if not all_events:
            return []

        # カウント
        counter = Counter(all_events)

        # カテゴリー別に分類
        categorized = {}
        for event, count in counter.items():
            category = self._get_category(event)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append({
                "event": event,
                "count": count,
                "category": category
            })

        # 各カテゴリー内で出現回数順にソート
        for category in categorized:
            categorized[category].sort(key=lambda x: x['count'], reverse=True)

        # カテゴリーの優先順位（定義されていない場合は出現順）
        if PRIORITY_CATEGORIES:
            priority_order = list(PRIORITY_CATEGORIES.keys()) + ['other']
        else:
            priority_order = ['other']

        # カテゴリー順に結合
        result = []
        for category in priority_order:
            if category in categorized:
                result.extend(categorized[category])

        return result

    def aggregate_data(self, slot_data: Dict[str, List[Dict]]) -> Dict:
        """収集したデータを集計して結果形式を生成"""
        print("📊 データ集計開始...")

        # Step 1: time_blocks作成（フィルタリング + 統合適用）
        time_blocks = self._create_time_blocks(slot_data)

        # Step 2: summary_ranking作成（time_blocksから集計 + カテゴリー分け）
        summary_ranking = self._create_summary_ranking(time_blocks)

        result = {
            "summary_ranking": summary_ranking,
            "time_blocks": time_blocks
        }

        total_events = sum(item["count"] for item in summary_ranking)
        print(f"✅ 集計完了: 総イベント数 {total_events}, ユニークイベント数 {len(summary_ranking)}")
        return result

    async def save_to_supabase(self, result: Dict, device_id: str, date: str) -> bool:
        """結果をSupabaseのaudio_aggregatorテーブルに保存"""
        try:
            # Supabaseにデータを保存（UPSERT）
            # summary_rankingは保存せず、time_blocksのみ保存（アプリ側で計算）
            response = self.supabase.table('audio_aggregator').upsert({
                'device_id': device_id,
                'date': date,
                'behavior_aggregator_result': result['time_blocks'],  # time_blocksを保存
                'behavior_aggregator_processed_at': datetime.utcnow().isoformat()
            }).execute()

            print(f"💾 Supabase保存完了: audio_aggregator テーブル")
            print(f"   device_id: {device_id}, date: {date}")
            print(f"   behavior_aggregator_result に time_blocks を保存")
            return True

        except Exception as e:
            print(f"❌ Supabase保存エラー: {e}")
            return False

    async def run(self, device_id: str, date: str) -> dict:
        """メイン処理実行

        Args:
            device_id: デバイスID
            date: 対象日付（YYYY-MM-DD形式）
        """
        print(f"🚀 SED集計処理開始: {device_id}, {date}")

        # Supabaseからデータ取得
        slot_data = await self.fetch_all_data(device_id, date)

        if not slot_data:
            print(f"⚠️ {date}のデータがありません")
            return {"success": False, "reason": "no_data", "message": f"{date}のデータがありません"}

        # データ集計
        result = self.aggregate_data(slot_data)

        # Supabaseに保存
        success = await self.save_to_supabase(result, device_id, date)

        if success:
            print("🎉 SED集計処理完了")
            return {"success": True, "message": "処理完了", "result": result}
        else:
            return {"success": False, "reason": "save_error", "message": "データの保存に失敗しました"}


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
    result = await aggregator.run(args.device_id, args.date)

    if result["success"]:
        print(f"\n✅ 処理完了")
        print(f"💾 データはSupabaseのaudio_aggregatorテーブルに保存されました")
    else:
        print(f"\n❌ 処理失敗: {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())
