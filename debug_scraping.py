#!/usr/bin/env python3
"""
25日のスケジュール抜け落ち問題のデバッグスクリプト
"""

import sys
import os
from datetime import datetime
import logging
import json
import requests
from bs4 import BeautifulSoup

# プロジェクト内モジュールをインポート
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from scraper import ScheduleScraper

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def debug_html_structure():
    """
    実際のHTMLを取得して構造を分析する
    """
    url = 'https://aikatsu-academy.com/schedule/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 25日の要素を具体的に探す
        print("=== 25日の要素を検索 ===")
        
        # 数字25を含む要素を探す
        num_25_elements = soup.find_all(string="25")
        print(f"「25」を含む要素数: {len(num_25_elements)}")
        
        for i, elem in enumerate(num_25_elements):
            parent = elem.parent
            if parent:
                print(f"\n--- 25日要素 {i+1} ---")
                print(f"親要素: {parent.name}")
                print(f"親要素クラス: {parent.get('class', [])}")
                print(f"親要素HTML: {str(parent)[:200]}...")
                
                # さらに上の親要素も確認
                grandparent = parent.parent
                if grandparent:
                    print(f"祖親要素: {grandparent.name}")
                    print(f"祖親要素クラス: {grandparent.get('class', [])}")
        
        # p-schedule-body__item の構造を確認
        print("\n=== p-schedule-body__item の構造確認 ===")
        schedule_items = soup.find_all('div', class_='p-schedule-body__item')
        print(f"p-schedule-body__item の数: {len(schedule_items)}")
        
        for i, item in enumerate(schedule_items):
            # data要素を探す
            data_elem = item.find('div', class_=lambda x: x and x.startswith('data'))
            if data_elem:
                num_elem = data_elem.find('div', class_='num')
                if num_elem:
                    day = num_elem.get_text().strip()
                    if day == "25":
                        print(f"\n--- 25日のp-schedule-body__item見つかりました（要素{i+1}） ---")
                        print(f"アイテム全体: {str(item)[:500]}...")
                        
                        # post__itemの数を確認
                        post_items = item.find_all('div', class_='post__item')
                        print(f"post__item数: {len(post_items)}")
                        
                        for j, post_item in enumerate(post_items):
                            print(f"  post__item {j+1}: {str(post_item)[:100]}...")
        
        # スケジュールスライドの確認
        print("\n=== スケジュールスライドの確認 ===")
        schedule_slides = soup.select('.swiper-container.js-schedule-body .swiper-slide')
        print(f"スケジュールスライド数: {len(schedule_slides)}")
        
        return soup
        
    except Exception as e:
        logger.error(f"HTML取得エラー: {e}")
        return None


def debug_scraper_processing():
    """
    スクレイパーの処理を詳しく確認する
    """
    print("\n=== スクレイパー処理のデバッグ ===")
    
    scraper = ScheduleScraper()
    
    # 実際のスケジュール取得
    schedule_data = scraper.fetch_schedule()
    
    print(f"取得されたスケジュール総数: {len(schedule_data)}")
    
    # 25日のデータを探す
    day_25_events = [event for event in schedule_data if event['day'] == 25]
    print(f"25日のイベント数: {len(day_25_events)}")
    
    if day_25_events:
        print("=== 25日のイベント詳細 ===")
        for i, event in enumerate(day_25_events):
            print(f"イベント {i+1}:")
            print(f"  日付: {event['year']}/{event['month']}/{event['day']}")
            print(f"  時刻: {event['hour']}:{event['minute']:02d}")
            print(f"  タイトル: {event['title']}")
            print(f"  カテゴリ: {event['category']}")
            print(f"  原文: {event.get('raw_text', '')[:100]}...")
            print()
    else:
        print("❌ 25日のイベントが見つかりませんでした")
        
        # 他の日のデータをサンプル表示
        print("\n=== 取得された他の日のサンプル ===")
        for event in schedule_data[:5]:
            print(f"{event['month']}/{event['day']} {event['hour']}:{event['minute']:02d} - {event['title']}")
    
    # JSON形式で保存
    output_file = 'debug_schedule_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schedule_data, f, ensure_ascii=False, indent=2)
    print(f"\nスケジュールデータを {output_file} に保存しました")
    
    return schedule_data


def main():
    """
    メイン関数
    """
    print("25日スケジュール抜け落ち問題のデバッグを開始します")
    print("=" * 60)
    
    # 1. HTML構造の調査
    soup = debug_html_structure()
    
    # 2. スクレイパー処理の調査
    schedule_data = debug_scraper_processing()
    
    print("\nデバッグ完了")


if __name__ == "__main__":
    main() 