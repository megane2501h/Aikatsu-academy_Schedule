#!/usr/bin/env python3
"""
API処理と分離したスクレーパー専用スクリプト
スケジュールを取得してCSVとJSONに出力
"""

import sys
import os
import csv
import json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scraper import ScheduleScraper

def main():
    """
    スケジュールを取得してCSV・JSON形式で出力
    """
    print("=== アイカツアカデミー！スケジュール取得 ===")
    
    scraper = ScheduleScraper()
    
    # 設定確認
    print("\n=== 設定確認 ===")
    print(f"カテゴリ絵文字: {scraper.category_emojis}")
    print(f"人物絵文字: {scraper.person_emojis}")
    print(f"特別キーワード: {scraper.special_keywords}")
    
    # スケジュール取得
    print("\n=== スケジュール取得 ===")
    schedule_data = scraper.fetch_schedule()
    
    if not schedule_data:
        print("❌ スケジュールデータが取得できませんでした")
        return
    
    print(f"✅ 取得件数: {len(schedule_data)}件")
    
    # outputフォルダを作成（存在しない場合）
    os.makedirs("output", exist_ok=True)
    
    # 固定ファイル名（上書き保存）
    csv_file = "output/schedule.csv"
    json_file = "output/schedule.json"
    
    # CSV出力
    print(f"\n=== CSV出力: {csv_file} ===")
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['日時', '絵文字', 'タイトル', '生データ']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for event in schedule_data:
            writer.writerow({
                '日時': f"{event['year']}/{event['month']:02d}/{event['day']:02d} {event['hour']:02d}:{event['minute']:02d}",
                '絵文字': event['category'],
                'タイトル': event['title'],
                '生データ': event['raw_text']
            })
    
    # JSON出力
    print(f"=== JSON出力: {json_file} ===")
    with open(json_file, 'w', encoding='utf-8') as jsonfile:
        json.dump(schedule_data, jsonfile, ensure_ascii=False, indent=2)
    
    # 絵文字統計
    print("\n=== 絵文字統計 ===")
    emoji_stats = {}
    no_emoji_count = 0
    
    for event in schedule_data:
        emoji = event['category']
        if emoji:
            emoji_stats[emoji] = emoji_stats.get(emoji, 0) + 1
        else:
            no_emoji_count += 1
    
    print(f"絵文字なし: {no_emoji_count}件")
    for emoji, count in sorted(emoji_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"'{emoji}': {count}件")
    
    # 品質チェック
    print("\n=== 品質チェック ===")
    if no_emoji_count == 0:
        print("✅ すべてのイベントに絵文字が設定されています")
    else:
        print(f"⚠️  絵文字なしのイベント: {no_emoji_count}件")
        
    # 複数絵文字チェック
    multi_emoji_events = [e for e in schedule_data if len(e['category']) > 2]
    if multi_emoji_events:
        print(f"⚠️  複数絵文字のイベント: {len(multi_emoji_events)}件")
        for event in multi_emoji_events[:3]:
            print(f"   '{event['category']}': {event['title']}")
    else:
        print("✅ 一つのイベントに一つの絵文字が設定されています")
    
    print(f"\n=== 出力完了 ===")
    print(f"CSV: {csv_file}")
    print(f"JSON: {json_file}")

if __name__ == "__main__":
    main() 