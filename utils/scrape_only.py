#!/usr/bin/env python3
"""
API処理と分離したスクレーパー専用スクリプト
スケジュールを取得してCSVとJSONに出力
Google Calendar API認証の問題を回避してテストできます
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
    print("※ このスクリプトはGoogle Calendar APIを使用しません")
    print("※ スクレーピングのみのテストが可能です")
    
    try:
        # 設定ファイルのパスを指定
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
        
        # 設定ファイルが存在しない場合はテンプレートを使用
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini.template')
        
        if not os.path.exists(config_path):
            print("⚠️  設定ファイルが見つかりません。デフォルト設定を使用します。")
            scraper = ScheduleScraper()
        else:
            print(f"✅ 設定ファイルを読み込み: {config_path}")
            scraper = ScheduleScraper(config_path)
        
        # 設定確認
        print("\n=== 設定確認 ===")
        print(f"カテゴリ絵文字: {scraper.category_emojis}")
        print(f"チャンネル絵文字: {scraper.channel_emojis}")
        print(f"特別キーワード: {scraper.special_keywords}")
        
        # スケジュール取得
        print("\n=== スケジュール取得 ===")
        schedule_data = scraper.fetch_schedule()
        
        if not schedule_data:
            print("❌ スケジュールデータが取得できませんでした")
            print("   - ネットワーク接続を確認してください")
            print("   - ウェブサイトの構造が変更されている可能性があります")
            return
        
        print(f"✅ 取得件数: {len(schedule_data)}件")
        
        # outputフォルダを作成（存在しない場合）
        os.makedirs("output", exist_ok=True)
        
        # タイムスタンプ付きファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"output/schedule_{timestamp}.csv"
        json_file = f"output/schedule_{timestamp}.json"
        
        # 固定ファイル名（上書き保存）
        csv_fixed = "output/schedule.csv"
        json_fixed = "output/schedule.json"
        
        # CSV出力
        print(f"\n=== CSV出力 ===")
        for file_path in [csv_file, csv_fixed]:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
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
        
        print(f"✅ CSV出力完了: {csv_file}")
        print(f"✅ CSV出力完了: {csv_fixed}")
        
        # JSON出力
        print(f"=== JSON出力 ===")
        for file_path in [json_file, json_fixed]:
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(schedule_data, jsonfile, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON出力完了: {json_file}")
        print(f"✅ JSON出力完了: {json_fixed}")
        
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
        
        # サマリー出力
        print(f"\n=== 処理完了 ===")
        print(f"CSV: {csv_file}")
        print(f"JSON: {json_file}")
        print(f"固定ファイル: {csv_fixed}, {json_fixed}")
        print(f"取得件数: {len(schedule_data)}件")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        print(f"エラー詳細: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main() 