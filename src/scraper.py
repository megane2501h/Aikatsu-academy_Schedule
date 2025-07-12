"""
アイカツアカデミー！スケジュール取得モジュール

アイカツアカデミー！公式サイトからスケジュール情報を
取得・解析するためのモジュールです。

主な機能:
- HTMLの解析とスケジュール抽出
- 絵文字による分類
- 構造化データの生成
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime, timedelta
import configparser
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScheduleScraper:
    """
    アイカツアカデミー！公式サイトからスケジュールを取得するクラス
    
    公式サイトのHTMLを解析してスケジュール情報を構造化データとして抽出します。
    """
    
    def __init__(self, config_path: str = "config.ini"):
        """
        初期化処理
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        self.target_url = self.config.get('DEFAULT', 'TARGET_URL', 
                                         fallback='https://aikatsu-academy.com/schedule/')
        
        # 設定ファイルから絵文字マッピングを読み込み
        self._load_emoji_settings()
    
    def _load_emoji_settings(self):
        """
        設定ファイルから絵文字関連の設定を読み込み
        """
        # カテゴリ → 絵文字マッピング（DEFAULTセクションの値を除外）
        self.category_emojis = {}
        if self.config.has_section('CategoryEmojis'):
            self.category_emojis = {k: v for k, v in self.config.items('CategoryEmojis') 
                                  if k not in self.config.defaults()}
        
        # チャンネル → 絵文字マッピング（DEFAULTセクションの値を除外）
        self.channel_emojis = {}
        if self.config.has_section('ChannelEmojis'):
            self.channel_emojis = {k: v for k, v in self.config.items('ChannelEmojis') 
                                if k not in self.config.defaults()}
        
        # 特別キーワード → 絵文字マッピング（最優先、DEFAULTセクションの値を除外）
        self.special_keywords = {}
        if self.config.has_section('SpecialKeywords'):
            self.special_keywords = {k: v for k, v in self.config.items('SpecialKeywords') 
                                    if k not in self.config.defaults()}
        
        # チャンネルURL → 配信者マッピング（DEFAULTセクションの値を除外）
        self.channel_urls = {}
        if self.config.has_section('ChannelURLs'):
            self.channel_urls = {k: v for k, v in self.config.items('ChannelURLs') 
                               if k not in self.config.defaults()}
        
        # 🐛 絵文字設定のデバッグ情報を出力
        logger.info(f"絵文字設定読み込み完了:")
        logger.info(f"  カテゴリ絵文字: {self.category_emojis}")
        logger.info(f"  チャンネル絵文字: {self.channel_emojis}")
        logger.info(f"  特別キーワード: {self.special_keywords}")
        logger.info(f"  チャンネルURL: {len(self.channel_urls)}件")
    
    def fetch_schedule(self) -> List[Dict[str, Any]]:
        """
        公式サイトからスケジュール情報を取得して構造化データに変換（高速化版）
        
        Returns:
            List[Dict]: 取得したスケジュールデータのリスト
        """
        try:
            logger.info(f"スケジュール取得開始: {self.target_url}")
            
            # 🚀 最適化：HTTPリクエストの高速化
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 🚀 最適化：セッションの使用とタイムアウト短縮
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(self.target_url, timeout=15)  # タイムアウト短縮
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 🚀 最適化：HTMLパーサーの使用
            soup = BeautifulSoup(response.text, 'html.parser')  # 標準HTMLパーサーを使用
            
            # サイト構造に応じた本文抽出器を使用
            schedule_data = self._extract_schedule_data_optimized(soup)
            
            logger.info(f"スケジュール取得完了: {len(schedule_data)}件")
            return schedule_data
            
        except requests.RequestException as e:
            logger.error(f"HTTP請求エラー: {e}")
            return []
        except Exception as e:
            logger.error(f"スケジュール取得エラー: {e}")
            return []
    
    def _extract_schedule_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        アイカツアカデミー！サイト専用の本文抽出器
        
        サイト構造に特化した抽出ロジック:
        - 月ヘッダーから年月情報を正確に抽出
        - スケジュールスライドと月ヘッダーを正確に対応付け
        - p-schedule-body__item から各日のスケジュールを取得
        - data要素から日付情報を抽出  
        - post__item から個別のイベント情報を抽出
        
        Args:
            soup: BeautifulSoupオブジェクト
            
        Returns:
            List[Dict]: 抽出したスケジュールデータ
        """
        schedule_data = []
        
        # 月ヘッダーから年月情報を取得（古いコードのロジックに従う）
        month_headers = soup.find_all('div', class_='swiper-slide', string=re.compile(r'\d{4}\.\d{1,2}'))
        month_changes = []
        for header in month_headers:
            match = re.search(r'(\d{4})\.(\d{1,2})', header.text)
            if match:
                year, month = map(int, match.groups())
                month_changes.append((year, month))
        
        if not month_changes:
            logger.warning("月ヘッダーが見つかりませんでした")
            return []
        
        logger.info(f"検出された月: {month_changes}")
        
        # スケジュールスライドを取得
        schedule_slides = soup.select('.swiper-container.js-schedule-body .swiper-slide')
        logger.info(f"スケジュールスライド数: {len(schedule_slides)}")
        
        if not schedule_slides:
            logger.warning("スケジュールスライドが見つかりませんでした")
            return []
        
        # 各スライドを処理（月ヘッダーとの対応付け）
        for slide_index, slide in enumerate(schedule_slides):
            if slide_index < len(month_changes):
                current_year, current_month = month_changes[slide_index]
                logger.debug(f"スライド{slide_index}: {current_year}年{current_month}月")
            else:
                # フォールバック: 最後の月情報を使用
                current_year, current_month = month_changes[-1]
                logger.warning(f"スライド{slide_index}: 月情報不足、{current_year}年{current_month}月を使用")
            
            # スライド内の各日のスケジュールアイテムを取得
            schedule_items = slide.find_all('div', class_='p-schedule-body__item')
            
            for item in schedule_items:
                # 日付情報を取得
                date_info = self._extract_date_from_item(item, current_year, current_month)
                if not date_info:
                    continue
                    
                year, month, day = date_info
                
                # その日のイベント一覧を取得
                post_items = item.find_all('div', class_='post__item')
                
                for post_item in post_items:
                    event_data = self._extract_event_from_post(post_item, year, month, day)
                    if event_data:
                        schedule_data.append(event_data)
        
        if not schedule_data:
            logger.warning("スケジュールデータが取得できませんでした")
        else:
            logger.info(f"スケジュールデータ取得成功: {len(schedule_data)}件")
        
        return sorted(schedule_data, key=lambda x: (x['year'], x['month'], x['day'], x['hour'], x['minute']))
    
    def _extract_date_from_item(self, item, current_year: int, current_month: int) -> tuple:
        """
        スケジュールアイテムから日付情報を抽出（古いコードのparse_date関数に準拠）
        
        Args:
            item: p-schedule-body__item要素
            current_year: 年（スライドから取得済み）
            current_month: 月（スライドから取得済み）
            
        Returns:
            tuple: (year, month, day) または None
        """
        # data要素から日付を取得
        data_elem = item.find('div', class_=re.compile(r'^data'))
        if not data_elem:
            return None
            
        # 日付の数字を取得
        num_elem = data_elem.find('div', class_='num')
        if not num_elem:
            return None
            
        try:
            day = int(num_elem.get_text().strip())
        except ValueError:
            return None
        
        # 古いコードのロジックに従い、スライドから取得した年月をそのまま使用
        return (current_year, current_month, day)
    
    def _extract_event_from_post(self, post_item, year: int, month: int, day: int) -> Dict[str, Any]:
        """
        post__item要素から個別のイベント情報を抽出（古いコードのロジックに準拠）
        
        Args:
            post_item: post__item要素
            year, month, day: 日付情報
            
        Returns:
            Dict: イベントデータまたはNone
        """
        # カテゴリ情報を取得（古いコードのparse_categories相当）
        categories = []
        cat_elems = post_item.find_all('div', class_='cat')
        for cat in cat_elems:
            cat_text = cat.get_text().strip()
            # カテゴリ置換（設定ファイルから読み込み）
            categories.append(self.category_emojis.get(cat_text, cat_text))
        
        # 説明文を取得（古いコードのparse_description相当）
        description_elem = post_item.find('p')
        if not description_elem:
            return None
            
        description = description_elem.get_text().strip()
        
        # 説明文の整形（古いコードのDESCRIPTION_REPLACEMENTSに準拠）
        description_replacements = {
            r'「アイカツアカデミー！配信部」': '',
            r'アイカツアカデミー！': '',
            r'【アイカツアカデミー！カード': '【カード',
        }
        for pattern, replacement in description_replacements.items():
            description = re.sub(pattern, replacement, description)
        
        # 時刻抽出（古いコードのextract_time相当）
        time_match = re.search(r'(\d{1,2}:\d{2})〜?\s*', description)
        time_specified = False  # 時刻が確定しているかのフラグ
        
        if time_match:
            time_str = time_match.group(1)
            hour, minute = map(int, time_str.split(':'))
            # 時刻を説明文から除去
            description = re.sub(r'\d{1,2}:\d{2}〜?\s*', '', description)
            time_specified = True
        else:
            # デフォルトの時刻設定
            hour, minute = 12, 0
        
        # デミカツ通信の特別処理（古いコードに準拠）
        if "デミカツ通信" in description:
            hour, minute = 20, 0
            time_specified = True  # デミカツ通信は時刻確定扱い
        
        # タイトル処理：すべての角括弧[]をタイトルから抽出して後ろに移動
        title = description
        
        # すべての角括弧を抽出
        bracket_contents = []
        
        # 1. 個人配信/個人chを配信/動画に変換
        if re.search(r'\[.*?個人配信\]', title):
            bracket_contents.append("[配信]")
            title = re.sub(r'\[.*?個人配信\]', '', title)
        elif re.search(r'\[.*?個人ch\]', title):
            bracket_contents.append("[動画]")
            title = re.sub(r'\[.*?個人ch\]', '', title)
        
        # 2. 配信部を配信に変換
        if re.search(r'\[.*?配信部\]', title):
            bracket_contents.append("[配信]")
            title = re.sub(r'\[.*?配信部\]', '', title)
        
        # 3. 既存の[配信]や[動画]を抽出
        existing_brackets = re.findall(r'\[(配信|動画)\]', title)
        for bracket in existing_brackets:
            bracket_contents.append(f"[{bracket}]")
        title = re.sub(r'\[(配信|動画)\]', '', title)
        
        # 4. その他すべての角括弧を抽出
        other_brackets = re.findall(r'\[[^\]]+\]', title)
        bracket_contents.extend(other_brackets)
        title = re.sub(r'\[[^\]]+\]', '', title)
        
        # 5. 重複削除と結合
        unique_brackets = []
        seen = set()
        for bracket in bracket_contents:
            if bracket not in seen:
                unique_brackets.append(bracket)
                seen.add(bracket)
        
        type_tag = ''.join(unique_brackets)
        
        # 全角スペースやタブを削除して整形
        title = title.strip()
        
        # 絵文字決定処理（優先順位: 特別キーワード > 複数絵文字組み合わせ > 人物 > カテゴリ）
        emoji = ""
        
        # 1. 特別キーワードを最優先でチェック（元の生データからも検索）
        original_text = post_item.get_text().strip()
        for keyword, special_emoji in self.special_keywords.items():
            if keyword in description or keyword in original_text:
                emoji = special_emoji
                break
        
        # 2. 特別キーワードがない場合、複数絵文字の組み合わせをチェック
        if not emoji:
            # カテゴリ絵文字と人物絵文字の組み合わせをチェック
            category_emoji = ""
            person_emoji = ""
            
            # カテゴリ絵文字を取得
            for cat in post_item.find_all('div', class_='cat'):
                cat_text = cat.get_text().strip()
                if cat_text in self.category_emojis:
                    category_emoji = self.category_emojis[cat_text]
                    break
            
            # 人物絵文字を取得
            for person, p_emoji in self.person_emojis.items():
                if person in description:
                    person_emoji = p_emoji
                    break
            
            # 複数絵文字の組み合わせ
            if person_emoji and category_emoji:
                emoji = person_emoji + category_emoji
            elif any("メンバーシップ" in cat_text for cat_text in [cat.get_text().strip() for cat in post_item.find_all('div', class_='cat')]):
                # メンバーシップ + 個人名配信の場合：個人絵文字👑
                personal_names = ["たいむ", "メエ", "パリン", "みえる"]
                if any(name in description for name in personal_names):
                    for person, p_emoji in self.person_emojis.items():
                        if person in description:
                            emoji = p_emoji + "👑"
                            break
        
        # 3. 複数絵文字でない場合、人物の絵文字を確認
        if not emoji:
            for person, person_emoji in self.person_emojis.items():
                if person in description:
                    emoji = person_emoji
                    break
        
        # 4. 人物絵文字もない場合、カテゴリから絵文字を取得
        if not emoji:
            for cat in categories:
                if cat in self.category_emojis.values():
                    emoji = cat
                    break
        
        # 5. 祝日イベントは除外（カレンダーに登録しない）
        if "祝日" in description:
            return None
        
        # 6. チャンネルURL決定（raw_textから元の角括弧を抽出）
        channel_url = ""
        original_text = post_item.get_text().strip()
        
        # 角括弧内容を抽出してチャンネルURLを検索
        bracket_matches = re.findall(r'\[([^\]]+)\]', original_text)
        for bracket_content in bracket_matches:
            if bracket_content in self.channel_urls:
                channel_url = self.channel_urls[bracket_content]
                break
        
        # フォールバック: 何も該当しない場合は公式サイトを追加
        if not channel_url:
            channel_url = "https://aikatsu-academy.com/ https://aikatsu-academy.com/schedule/"
        
        if title.strip():  # タイトルが空でない場合のみ
            return {
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": minute,
                "title": title.strip(),
                "category": emoji,
                "type_tag": type_tag,
                "raw_text": post_item.get_text().strip(),
                "time_specified": time_specified,  # 時刻が確定しているかのフラグ
                "channel_url": channel_url  # チャンネルURLを追加
            }
        
        return None
    
    def _extract_schedule_data_optimized(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        アイカツアカデミー！サイト専用の本文抽出器（高速化版）
        
        Args:
            soup: BeautifulSoupオブジェクト
            
        Returns:
            List[Dict]: 抽出したスケジュールデータ
        """
        schedule_data = []
        
        # 🚀 最適化：一度に全要素を取得
        month_headers = soup.find_all('div', class_='swiper-slide', string=re.compile(r'\d{4}\.\d{1,2}'))
        schedule_slides = soup.select('.swiper-container.js-schedule-body .swiper-slide')
        
        # 月ヘッダーから年月情報を取得
        month_changes = []
        for header in month_headers:
            match = re.search(r'(\d{4})\.(\d{1,2})', header.text)
            if match:
                year, month = map(int, match.groups())
                month_changes.append((year, month))
        
        if not month_changes:
            logger.warning("月ヘッダーが見つかりませんでした")
            return []
        
        logger.info(f"検出された月: {month_changes}")
        logger.info(f"スケジュールスライド数: {len(schedule_slides)}")
        
        if not schedule_slides:
            logger.warning("スケジュールスライドが見つかりませんでした")
            return []
        
        # 🚀 最適化：並列処理風の一括処理
        for slide_index, slide in enumerate(schedule_slides):
            if slide_index < len(month_changes):
                current_year, current_month = month_changes[slide_index]
            else:
                current_year, current_month = month_changes[-1]
            
            # 🚀 最適化：一度に全アイテムを取得
            schedule_items = slide.find_all('div', class_='p-schedule-body__item')
            
            for item in schedule_items:
                # 日付情報を取得
                date_info = self._extract_date_from_item_optimized(item, current_year, current_month)
                if not date_info:
                    continue
                    
                year, month, day = date_info
                
                # その日のイベント一覧を取得
                post_items = item.find_all('div', class_='post__item')
                
                for post_item in post_items:
                    event_data = self._extract_event_from_post_optimized(post_item, year, month, day)
                    if event_data:
                        schedule_data.append(event_data)
        
        if not schedule_data:
            logger.warning("スケジュールデータが取得できませんでした")
        else:
            logger.info(f"スケジュールデータ取得成功: {len(schedule_data)}件")
        
        return sorted(schedule_data, key=lambda x: (x['year'], x['month'], x['day'], x['hour'], x['minute']))
    
    def _extract_date_from_item_optimized(self, item, current_year: int, current_month: int) -> tuple:
        """
        スケジュールアイテムから日付情報を抽出（高速化版）
        """
        # 🚀 最適化：CSS選択を使用
        data_elem = item.select_one('div[class*="data"]')
        if not data_elem:
            return None
            
        num_elem = data_elem.select_one('div.num')
        if not num_elem:
            return None
            
        try:
            day = int(num_elem.get_text().strip())
        except ValueError:
            return None
        
        return (current_year, current_month, day)
    
    def _extract_event_from_post_optimized(self, post_item, year: int, month: int, day: int) -> Dict[str, Any]:
        """
        post__item要素から個別のイベント情報を抽出（高速化版）
        """
        # 🚀 最適化：CSS選択を使用
        cat_elems = post_item.select('div.cat')
        categories = []
        for cat in cat_elems:
            cat_text = cat.get_text().strip()
            categories.append(self.category_emojis.get(cat_text, cat_text))
        
        # 説明文を取得
        description_elem = post_item.select_one('p')
        if not description_elem:
            return None
            
        description = description_elem.get_text().strip()
        
        # 🚀 最適化：正規表現の事前コンパイル
        description_replacements = {
            r'「アイカツアカデミー！配信部」': '',
            r'アイカツアカデミー！': '',
            r'【アイカツアカデミー！カード': '【カード',
        }
        for pattern, replacement in description_replacements.items():
            description = re.sub(pattern, replacement, description)
        
        # 時刻抽出
        time_match = re.search(r'(\d{1,2}:\d{2})〜?\s*', description)
        time_specified = bool(time_match)
        
        if time_match:
            time_str = time_match.group(1)
            hour, minute = map(int, time_str.split(':'))
        else:
            hour, minute = 0, 0
        
        # タイトル抽出
        title = re.sub(r'^\d{1,2}:\d{2}〜?\s*', '', description).strip()
        
        # イベントデータを構築
        event_data = {
            'year': year,
            'month': month,
            'day': day,
            'hour': hour,
            'minute': minute,
            'title': title,
            'category': ''.join(categories),
            'raw_text': description,
            'time_specified': time_specified
        }
        
        # 🚀 最適化：絵文字とURL処理を一括で実行
        self._apply_emoji_and_url_optimized(event_data)
        
        return event_data
    
    def _apply_emoji_and_url_optimized(self, event_data: Dict[str, Any]) -> None:
        """
        絵文字とURL処理を一括で実行（高速化版）
        処理順序：
        1. チャンネル絵文字（[]内の内容から判定・最優先）
        2. 特別キーワード（2文字目として追加）
        3. カテゴリ絵文字（フォールバック）
        """
        title = event_data['title']
        original_category = event_data.get('category', '')
        
        # 🐛 デバッグ情報を出力
        logger.info(f"絵文字適用前: タイトル='{title}', カテゴリ='{original_category}'")
        
        # 1. チャンネル絵文字の適用（[]内の内容から判定・最優先）
        channel_emoji = ''
        # []内の内容を抽出
        import re
        bracket_match = re.search(r'\[([^\]]+)\]', title)
        if bracket_match:
            bracket_content = bracket_match.group(1)
            # チャンネル絵文字を検索
            for channel_name, emoji in self.channel_emojis.items():
                if channel_name in bracket_content:
                    channel_emoji = emoji
                    logger.info(f"チャンネル絵文字適用: '[{bracket_content}]' -> '{emoji}'")
                    break
        
        # 2. 特別キーワードの適用（2文字目として追加、複数可能）
        special_emoji = ''
        for keyword, emoji in self.special_keywords.items():
            if keyword in title:
                special_emoji += emoji
                logger.info(f"特別キーワード適用: '{keyword}' -> '{emoji}'")
        
        # 3. 絵文字の組み合わせ
        if channel_emoji:
            # チャンネル絵文字を1文字目に設定
            event_data['category'] = channel_emoji
            # 特別キーワードがあれば2文字目に追加
            if special_emoji:
                event_data['category'] += special_emoji
        elif special_emoji:
            # チャンネル絵文字がない場合は特別キーワードのみ
            event_data['category'] = special_emoji
        elif original_category:
            # フォールバック: 元のカテゴリ絵文字を維持
            event_data['category'] = original_category
            logger.info(f"カテゴリ絵文字維持: '{original_category}'")
        
        # 4. チャンネルURL処理
        event_data['channel_url'] = ''  # 初期化
        for channel_name, url in self.channel_urls.items():
            if channel_name in title:
                event_data['channel_url'] = url
                logger.info(f"チャンネルURL適用: '{channel_name}' -> '{url}'")
                break
        
        # 5. type_tag処理
        if '配信' in title:
            event_data['type_tag'] = '[配信]'
        elif '動画' in title:
            event_data['type_tag'] = '[動画]'
        else:
            event_data['type_tag'] = ''
        
        # 🐛 デバッグ情報を出力
        logger.info(f"絵文字適用後: タイトル='{title}', カテゴリ='{event_data.get('category', '')}', URL='{event_data.get('channel_url', '')}'")
        
        # フォールバック: 何も該当しない場合は公式サイトを追加
        if not event_data.get('channel_url'):
            event_data['channel_url'] = "https://aikatsu-academy.com/ https://aikatsu-academy.com/schedule/"
