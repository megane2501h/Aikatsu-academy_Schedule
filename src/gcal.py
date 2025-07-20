"""
Googleカレンダー連携モジュール

Google Calendar APIを使用してスケジュール情報を
カレンダーに同期するためのモジュールです。

主な機能:
- OAuth2.0認証（個人用・従来方式）
- サービスアカウント認証（企業用・推奨方式）
- 既存予定の削除
- 新規予定の一括登録
- 差分更新による高速同期
"""

import os
import pickle
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import configparser
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# BatchHttpRequestは self.service.new_batch_http_request() で作成

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/calendar']

# 定数定義
SAFETY_MARGIN_MONTHS = 3  # 安全マージン月数
BATCH_SIZE_LIMIT = 1000   # バッチ処理の上限
DEFAULT_EVENT_DURATION_HOURS = 1  # デフォルト予定時間


class GoogleCalendarManager:
    """
    Googleカレンダー操作を管理するクラス
    
    Google Calendar APIを使用して認証・予定操作を行います。
    差分更新により高速同期を実現します。
    """
    
    def __init__(self, config_path: str = "config.ini"):
        """
        初期化処理
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        self.calendar_id = self.config.get('GoogleCalendar', 'calendar_id')
        
        # 認証方式の設定（デフォルトはOAuth2）
        self.auth_method = self.config.get('GoogleCalendar', 'auth_method', fallback='oauth2')
        
        # OAuth2認証設定
        self.credentials_file = self.config.get('GoogleCalendar', 'credentials_file', 
                                               fallback='credentials.json')
        self.token_file = self.config.get('GoogleCalendar', 'token_file', 
                                         fallback='token.json')
        
        # サービスアカウント認証設定
        self.service_account_file = self.config.get('GoogleCalendar', 'service_account_file',
                                                   fallback='service-account.json')
        
        self.service = None
    
    def _calculate_date_range(self, events_data: List[Dict[str, Any]]) -> Tuple[datetime, datetime]:
        """
        スケジュールデータから同期対象の日付範囲を計算
        
        Args:
            events_data: スケジュールデータ
            
        Returns:
            Tuple[datetime, datetime]: (開始日, 終了日)
        """
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        
        if events_data:
            # データの最大日付を確認
            max_year = max(item['year'] for item in events_data)
            max_month = max(item['month'] for item in events_data if item['year'] == max_year)
            
            # 安全マージンを追加
            extended_year = max_year
            extended_month = max_month + SAFETY_MARGIN_MONTHS
            
            # 年の繰り上がりを処理
            while extended_month > 12:
                extended_month -= 12
                extended_year += 1
            
            # 終了日を計算
            if extended_month == 12:
                end_date = datetime(extended_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(extended_year, extended_month + 1, 1) - timedelta(days=1)
        else:
            # フォールバック: 現在から3ヶ月先まで
            end_date = datetime(now.year, now.month + SAFETY_MARGIN_MONTHS, 1) - timedelta(days=1)
        
        return start_date, end_date
    

    


    def authenticate(self) -> bool:
        """
        Google Calendar APIの認証を実行
        
        Returns:
            bool: 認証成功時True, 失敗時False
        """
        try:
            # 認証方式によって処理を分岐
            if self.auth_method == 'service_account':
                return self._authenticate_service_account()
            else:
                return self._authenticate_oauth2()
                
        except Exception as e:
            logger.error(f"認証エラー: {e}")
            return False
    
    def _authenticate_service_account(self) -> bool:
        """
        サービスアカウント認証を実行
        
        Returns:
            bool: 認証成功時True, 失敗時False
        """
        try:
            logger.info("サービスアカウント認証を開始...")
            
            # サービスアカウントファイルの確認
            if not os.path.exists(self.service_account_file):
                logger.error(f"サービスアカウントファイルが見つかりません: {self.service_account_file}")
                logger.error("🔧 解決方法:")
                logger.error("  1. Google Cloud Consoleでサービスアカウントを作成")
                logger.error("  2. JSONキーファイルをダウンロード")
                logger.error("  3. ファイルを正しいパスに配置")
                logger.error("  4. 詳細: docs/SERVICE_ACCOUNT_SETUP.md を参照")
                return False
            
            # サービスアカウント認証情報の読み込み
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=SCOPES)
                logger.info("サービスアカウント認証情報を正常に読み込みました")
            except Exception as e:
                logger.error(f"サービスアカウントファイルの読み込みエラー: {e}")
                logger.error("🔧 ファイル内容を確認してください:")
                logger.error("  - 有効なJSON形式か")
                logger.error("  - 正しいサービスアカウントキーか")
                return False
            
            # Google Calendar APIサービス構築
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("サービスアカウント認証完了 - Google Calendar API接続成功")
            return True
            
        except Exception as e:
            logger.error(f"サービスアカウント認証エラー: {e}")
            return False
    
    def _authenticate_oauth2(self) -> bool:
        """
        OAuth2認証を実行（従来方式）
        
        Returns:
            bool: 認証成功時True, 失敗時False
        """
        try:
            creds = None
            
            # 既存のトークンファイル確認
            if os.path.exists(self.token_file):
                try:
                    creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                except Exception as e:
                    logger.warning(f"トークンファイルの読み込みエラー: {e}")
                    creds = None
            
            # トークンが無効または存在しない場合
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # トークンのリフレッシュ（改善版・リトライ機能付き）
                    logger.info("アクセストークンをリフレッシュ中...")
                    refresh_success = False
                    
                    # リフレッシュのリトライ（最大3回）
                    for attempt in range(1, 4):
                        try:
                            creds.refresh(Request())
                            logger.info(f"トークンリフレッシュ成功 (試行回数: {attempt})")
                            refresh_success = True
                            break
                        except Exception as e:
                            logger.warning(f"トークンリフレッシュ試行{attempt}失敗: {e}")
                            if attempt < 3:
                                import time
                                wait_time = attempt * 2  # 2秒、4秒の間隔でリトライ
                                logger.info(f"{wait_time}秒後にリトライします...")
                                time.sleep(wait_time)
                            else:
                                logger.error(f"トークンリフレッシュ完全失敗: {e}")
                    
                    if not refresh_success:
                        logger.info("新しいトークンが必要です")
                        creds = None
                
                # リフレッシュに失敗した場合または初回認証の場合
                if not creds or not creds.valid:
                    # GitHub Actions環境かどうかを判定
                    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
                    
                    if is_github_actions:
                        # GitHub Actions環境では、事前に設定されたトークンファイルを使用
                        logger.error("GitHub Actions環境でトークンが無効です")
                        logger.error("🔧 トークンの問題が発生しました:")
                        logger.error("  1. GOOGLE_TOKEN secretの有効期限が切れている可能性があります")
                        logger.error("  2. ローカルで新しいトークンを生成してください:")
                        logger.error("     cd /path/to/your/project")
                        logger.error("     python src/main.py --manual")
                        logger.error("  3. 生成されたtoken.jsonの内容をGitHubのsecretsに設定:")
                        logger.error("     - Repository Settings > Secrets and variables > Actions")
                        logger.error("     - GOOGLE_TOKEN secretを新しいtoken.jsonの内容で更新")
                        logger.error("  4. 必要に応じてGOOGLE_CREDENTIALSも最新版に更新")
                        logger.error("  5. スクレーピング機能の確認は utils/scrape_only.py で可能です")
                        
                        # トークン状態の詳細情報
                        if creds:
                            if creds.expired:
                                logger.error(f"  🚨 トークン状態: 期限切れ (有効期限: {creds.expiry})")
                            else:
                                logger.error("  🚨 トークン状態: 無効または破損")
                            if not creds.refresh_token:
                                logger.error("  🚨 リフレッシュトークンが利用できません")
                        else:
                            logger.error("  🚨 トークン状態: 読み込み不可または存在しません")
                        
                        return False
                    else:
                        # ローカル環境では対話的認証を実行
                        logger.info("OAuth認証を開始...")
                        if not os.path.exists(self.credentials_file):
                            logger.error(f"認証情報ファイルが見つかりません: {self.credentials_file}")
                            return False
                        
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, SCOPES)
                        creds = flow.run_local_server(port=0)
                        logger.info("ローカル認証完了")
                
                # トークンを保存
                try:
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("認証トークンを保存しました")
                except Exception as e:
                    logger.warning(f"トークンの保存に失敗しました: {e}")
                
                logger.info("認証完了")
            
            # Google Calendar APIサービス構築
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar API接続成功")
            return True
            
        except Exception as e:
            logger.error(f"認証エラー: {e}")
            return False
    
    def clear_events(self, start_date: datetime, end_date: datetime) -> bool:
        """
        指定期間のカレンダー予定をすべて削除（高速化バッチ処理対応）
        
        Args:
            start_date: 削除開始日時
            end_date: 削除終了日時
            
        Returns:
            bool: 削除成功時True, 失敗時False
        """
        if not self.service:
            logger.error("Google Calendar APIが初期化されていません")
            return False

        try:
            logger.info(f"既存予定削除開始: {start_date.date()} ～ {end_date.date()}")
            
            # 🚀 最適化：削除対象の事前フィルタリング
            # 削除対象を絞り込むためのクエリを改善
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                maxResults=2500,  # 最大件数を指定して高速化
                showDeleted=False  # 削除済みイベントを除外
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                logger.info("削除対象の予定がありません")
                return True
            
            # 🚀 最適化：削除対象の事前フィルタリング強化
            # アイカツアカデミー関連の予定のみを削除対象にする
            filtered_events = []
            for event in events:
                title = event.get('summary', '')
                description = event.get('description', '')
                
                # アイカツアカデミー関連の予定を特定
                if any(keyword in title for keyword in ['アイカツ', 'みえる', 'メエ', 'パリン', 'たいむ', '📱', '🎴', '🧸', '✨', '👑', '🩷', '💙', '💛', '💜', '📰', '💪', '🔥', '🗺️', '🏫']) or \
                   any(keyword in description for keyword in ['Hash: ', 'youtube.com/@', 'aikatsu-academy']):
                    filtered_events.append(event)
            
            if not filtered_events:
                logger.info("削除対象の予定がありません（フィルタリング後）")
                return True
            
            logger.info(f"削除対象: {len(filtered_events)}件（フィルタリング前: {len(events)}件）")
            
            # 🚀 最適化：バッチサイズの最適化（小さいバッチサイズで高速化）
            optimized_batch_size = min(100, len(filtered_events))
            
            deleted_count = 0
            failed_count = 0
            
            def delete_callback(request_id, response, exception):
                nonlocal deleted_count, failed_count
                if exception is not None:
                    logger.debug(f"予定削除エラー (ID: {request_id}): {exception}")
                    failed_count += 1
                else:
                    deleted_count += 1
            
            # 🚀 最適化：効率的なバッチ処理
            total_events = len(filtered_events)
            
            if total_events <= optimized_batch_size:
                # 小規模バッチ処理（最適化版）
                batch = self.service.new_batch_http_request(callback=delete_callback)
                for event in filtered_events:
                    batch.add(
                        self.service.events().delete(
                            calendarId=self.calendar_id,
                            eventId=event['id']
                        ),
                        request_id=event['id']
                    )
                batch.execute()
                logger.info(f"一括削除完了: {total_events}件")
            else:
                # 大規模分割処理（最適化版）
                logger.info(f"大量データ検出: {total_events}件 → 分割処理開始")
                for i in range(0, total_events, optimized_batch_size):
                    batch_events = filtered_events[i:i + optimized_batch_size]
                    batch = self.service.new_batch_http_request(callback=delete_callback)
                    
                    for event in batch_events:
                        batch.add(
                            self.service.events().delete(
                                calendarId=self.calendar_id,
                                eventId=event['id']
                            ),
                            request_id=event['id']
                        )
                    
                    batch.execute()
                    logger.info(f"分割削除進捗: {min(i + optimized_batch_size, total_events)}/{total_events}")
            
            logger.info(f"既存予定削除完了: {deleted_count}件成功, {failed_count}件失敗")
            
            # 一部失敗があっても、大部分が成功していれば True を返す
            return deleted_count > 0 or total_events == 0
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.error("❌ カレンダーが見つかりません")
                logger.error(f"📝 設定されたカレンダーID: {self.calendar_id}")
                logger.error("🔧 修正方法:")
                logger.error("  1. config.iniのCALENDAR_IDを確認してください")
                logger.error("  2. Google Calendarでカレンダーの設定を開く")
                logger.error("  3. 「カレンダーの統合」からカレンダーIDをコピー")
                logger.error("  4. カレンダーが共有されていることを確認")
            else:
                logger.error(f"Google Calendar APIエラー: {e}")
            return False
        except Exception as e:
            logger.error(f"予定削除エラー: {e}")
            return False
    
    def create_events(self, events_data: List[Dict[str, Any]]) -> bool:
        """
        スケジュールデータからGoogleカレンダー予定を一括作成（高速化版）
        
        Args:
            events_data: scraper.pyから取得したスケジュールデータ
            
        Returns:
            bool: 作成成功時True, 失敗時False
        """
        if not self.service:
            logger.error("Google Calendar APIが初期化されていません")
            return False
        
        if not events_data:
            logger.info("作成する予定がありません")
            return True
        
        try:
            logger.info(f"予定作成開始: {len(events_data)}件")
            
            created_count = 0
            failed_count = 0
            failed_events = []
            
            def create_callback(request_id, response, exception):
                nonlocal created_count, failed_count
                if exception is not None:
                    logger.debug(f"予定作成エラー (ID: {request_id}): {exception}")
                    failed_count += 1
                    failed_events.append(request_id)
                else:
                    created_count += 1
                    logger.debug(f"予定作成成功: {request_id} (ID: {response.get('id')})")
            
            # 🚀 最適化：バッチサイズの最適化（作成処理用）
            optimized_batch_size = min(50, len(events_data))  # 作成処理は50件が最適
            total_events = len(events_data)
            
            # 🚀 最適化：効率的なバッチ処理
            if total_events <= optimized_batch_size:
                self._execute_single_batch_optimized(events_data, create_callback)
            else:
                self._execute_multiple_batches_optimized(events_data, optimized_batch_size, create_callback)
            
            logger.info(f"予定作成完了: {created_count}件成功, {failed_count}件失敗")
            
            # 失敗したイベントがある場合は警告
            if failed_events:
                logger.debug(f"作成に失敗したイベント: {', '.join(failed_events[:5])}{'...' if len(failed_events) > 5 else ''}")
            
            return created_count > 0
            
        except Exception as e:
            logger.error(f"予定作成エラー: {e}")
            return False
    
    def _generate_unique_request_id(self, event_data: Dict[str, Any]) -> str:
        """
        バッチリクエスト用の一意なIDを生成
        
        Args:
            event_data: イベントデータ
            
        Returns:
            str: 一意なrequest_id（日付+時刻+タイトル+タイムスタンプ形式）
        """
        timestamp = int(time.time() * 1000)  # ミリ秒単位のタイムスタンプ
        return f"{event_data['year']}-{event_data['month']:02d}-{event_data['day']:02d}_{event_data['hour']:02d}{event_data['minute']:02d}_{event_data['title']}_{timestamp}"
    
    def _create_event_object(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        イベントデータからGoogle Calendar用のイベントオブジェクトを作成
        
        Args:
            event_data: スケジュールデータ
            
        Returns:
            Dict: Google Calendar APIイベントオブジェクト
        """
        # タイトルに絵文字を追加
        title = event_data['title']
        emoji = event_data.get('category', '')
        type_tag = event_data.get('type_tag', '')
        
        # 🐛 絵文字適用のデバッグ情報
        logger.info(f"カレンダーイベント作成: '{title}' 絵文字='{emoji}' タグ='{type_tag}'")
        
        # 新しいタイトル形式: 絵文字 + タイトル + [配信/動画]
        if emoji:
            title = f"{emoji}{title}"
        if type_tag:
            title = f"{title}{type_tag}"
        
        # 🐛 最終タイトルを出力
        logger.info(f"最終タイトル: '{title}'")
        
        # 時刻が確定していないイベントを終日予定に変更
        if not event_data.get('time_specified', True):
            # 終日予定として作成
            event_date = datetime(
                event_data['year'],
                event_data['month'],
                event_data['day']
            ).date()
            
            # 終日予定の終了日は翌日
            end_date = event_date + timedelta(days=1)
            
            # description作成（チャンネルURL含む）
            description_parts = [f"原文: {event_data.get('raw_text', '')}"]
            if event_data.get('channel_url'):
                description_parts.append(f"URL: {event_data['channel_url']}")
            description = "\n".join(description_parts)
            
            return {
                'summary': title,
                'description': description,
                'start': {
                    'date': event_date.isoformat(),
                },
                'end': {
                    'date': end_date.isoformat(),
                },
                'visibility': 'public',
            }
        else:
            # 時刻が指定されている予定として作成
            start_datetime = datetime(
                event_data['year'],
                event_data['month'],
                event_data['day'],
                event_data['hour'],
                event_data['minute']
            )
            
            # 終了時刻（開始時刻+デフォルト時間）
            end_datetime = start_datetime + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)
            
            # description作成（チャンネルURL含む）
            description_parts = [f"原文: {event_data.get('raw_text', '')}"]
            if event_data.get('channel_url'):
                description_parts.append(f"チャンネル: {event_data['channel_url']}")
            description = "\n".join(description_parts)
            
            return {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'visibility': 'public',
            }
    
    def _execute_single_batch(self, events_data: List[Dict[str, Any]], callback) -> None:
        """
        一括バッチ処理（制限件数以下）
        """
        batch = self.service.new_batch_http_request(callback=callback)
        
        for event_data in events_data:
            try:
                event = self._create_event_object(event_data)
                unique_id = self._generate_unique_request_id(event_data)
                batch.add(
                    self.service.events().insert(
                        calendarId=self.calendar_id,
                        body=event
                    ),
                    request_id=unique_id
                )
            except Exception as e:
                logger.warning(f"イベントデータ準備エラー: {event_data.get('title', 'Unknown')} - {e}")
                continue
        
        batch.execute()
        logger.info(f"一括登録完了: {len(events_data)}件")
    
    def _execute_multiple_batches(self, events_data: List[Dict[str, Any]], max_batch_size: int, callback) -> None:
        """
        分割バッチ処理（制限件数超過）
        """
        total_events = len(events_data)
        logger.info(f"大量データ検出: {total_events}件 → 分割処理開始")
        
        for i in range(0, total_events, max_batch_size):
            batch_events = events_data[i:i + max_batch_size]
            batch = self.service.new_batch_http_request(callback=callback)
            
            for event_data in batch_events:
                try:
                    event = self._create_event_object(event_data)
                    unique_id = self._generate_unique_request_id(event_data)
                    batch.add(
                        self.service.events().insert(
                            calendarId=self.calendar_id,
                            body=event
                        ),
                        request_id=unique_id
                    )
                except Exception as e:
                    logger.warning(f"イベントデータ準備エラー: {event_data.get('title', 'Unknown')} - {e}")
                    continue
            
            batch.execute()
            logger.info(f"分割登録進捗: {min(i + max_batch_size, total_events)}/{total_events}")
    
    def _execute_single_batch_optimized(self, events_data: List[Dict[str, Any]], callback) -> None:
        """
        一括バッチ処理（最適化版）
        """
        batch = self.service.new_batch_http_request(callback=callback)
        
        for event_data in events_data:
            try:
                event = self._create_event_object(event_data)
                unique_id = self._generate_unique_request_id(event_data)
                batch.add(
                    self.service.events().insert(
                        calendarId=self.calendar_id,
                        body=event
                    ),
                    request_id=unique_id
                )
            except Exception as e:
                logger.debug(f"イベントデータ準備エラー: {event_data.get('title', 'Unknown')} - {e}")
                continue
        
        batch.execute()
        logger.info(f"一括登録完了: {len(events_data)}件")
    
    def _execute_multiple_batches_optimized(self, events_data: List[Dict[str, Any]], max_batch_size: int, callback) -> None:
        """
        分割バッチ処理（最適化版）
        """
        total_events = len(events_data)
        logger.info(f"大量データ検出: {total_events}件 → 最適化分割処理開始")
        
        for i in range(0, total_events, max_batch_size):
            batch_events = events_data[i:i + max_batch_size]
            batch = self.service.new_batch_http_request(callback=callback)
            
            for event_data in batch_events:
                try:
                    event = self._create_event_object(event_data)
                    unique_id = self._generate_unique_request_id(event_data)
                    batch.add(
                        self.service.events().insert(
                            calendarId=self.calendar_id,
                            body=event
                        ),
                        request_id=unique_id
                    )
                except Exception as e:
                    logger.debug(f"イベントデータ準備エラー: {event_data.get('title', 'Unknown')} - {e}")
                    continue
            
            batch.execute()
            logger.debug(f"分割登録進捗: {min(i + max_batch_size, total_events)}/{total_events}")
    
    def get_calendar_info(self) -> Optional[Dict[str, Any]]:
        """
        カレンダー情報を取得（デバッグ・確認用）
        
        Returns:
            Dict: カレンダー情報, エラー時None
        """
        if not self.service:
            return None
        
        try:
            calendar = self.service.calendars().get(calendarId=self.calendar_id).execute()
            return {
                'id': calendar.get('id'),
                'summary': calendar.get('summary'),
                'description': calendar.get('description'),
                'timeZone': calendar.get('timeZone'),
            }
        except Exception as e:
            logger.error(f"カレンダー情報取得エラー: {e}")
            return None

    def get_events_count(self, start_date: datetime, end_date: datetime) -> int:
        """
        指定期間のイベント数を取得（テスト・確認用）
        
        Args:
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            int: イベント数、エラー時-1
        """
        if not self.service:
            logger.error("Google Calendar APIが初期化されていません")
            return -1
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return len(events)
            
        except Exception as e:
            logger.error(f"イベント数取得エラー: {e}")
            return -1
    
    def list_events(self, start_date: datetime, end_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """
        指定期間のイベント一覧を取得（テスト・確認用）
        
        Args:
            start_date: 開始日時
            end_date: 終了日時
            limit: 取得件数上限
            
        Returns:
            List[Dict]: イベント一覧
        """
        if not self.service:
            logger.error("Google Calendar APIが初期化されていません")
            return []
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                maxResults=limit
            ).execute()
            
            events = events_result.get('items', [])
            result = []
            
            for event in events:
                event_info = {
                    'id': event.get('id'),
                    'summary': event.get('summary', ''),
                    'start': event.get('start', {}),
                    'end': event.get('end', {}),
                    'description': event.get('description', '')
                }
                result.append(event_info)
            
            return result
            
        except Exception as e:
            logger.error(f"イベント一覧取得エラー: {e}")
            return []

 