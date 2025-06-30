"""
Googleカレンダー連携モジュール

Google Calendar APIを使用してスケジュール情報を
カレンダーに同期するためのモジュールです。

主な機能:
- OAuth2.0認証
- 既存予定の削除
- 新規予定の一括登録
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import configparser
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# BatchHttpRequestは self.service.new_batch_http_request() で作成

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarManager:
    """
    Googleカレンダー操作を管理するクラス
    
    Google Calendar APIを使用して認証・予定操作を行います。
    """
    
    def __init__(self, config_path: str = "config.ini"):
        """
        初期化処理
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        self.calendar_id = self.config.get('GoogleCalendar', 'CALENDAR_ID')
        self.credentials_file = self.config.get('GoogleCalendar', 'CREDENTIALS_FILE', 
                                               fallback='credentials.json')
        self.token_file = self.config.get('GoogleCalendar', 'TOKEN_FILE', 
                                         fallback='token.json')
        self.service = None
    
    def authenticate(self) -> bool:
        """
        Google Calendar APIの認証を実行
        
        Returns:
            bool: 認証成功時True, 失敗時False
        """
        try:
            creds = None
            
            # 既存のトークンファイル確認
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            # トークンが無効または存在しない場合
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # トークンのリフレッシュ
                    logger.info("アクセストークンをリフレッシュ中...")
                    creds.refresh(Request())
                else:
                    # 新規OAuth認証
                    logger.info("OAuth認証を開始...")
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"認証情報ファイルが見つかりません: {self.credentials_file}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                
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
        指定期間のカレンダー予定をすべて削除（バッチ処理対応）
        
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
            
            # 指定期間の予定を取得
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                logger.info("削除対象の予定がありません")
                return True
            
            logger.info(f"削除対象: {len(events)}件")
            
            deleted_count = 0
            failed_count = 0
            
            def delete_callback(request_id, response, exception):
                nonlocal deleted_count, failed_count
                if exception is not None:
                    logger.warning(f"予定削除エラー (ID: {request_id}): {exception}")
                    failed_count += 1
                else:
                    deleted_count += 1
            
            # Google Calendar APIの制限：1000件/バッチ
            max_batch_size = 1000
            total_events = len(events)
            
            # 1000件以下の場合は一括処理、それ以上の場合は分割処理
            if total_events <= max_batch_size:
                # 一括削除（通常のケース）
                batch = self.service.new_batch_http_request(callback=delete_callback)
                for event in events:
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
                # 1000件を超える場合のみ分割処理
                logger.info(f"大量データ検出: {total_events}件 → 分割処理開始")
                for i in range(0, total_events, max_batch_size):
                    batch_events = events[i:i + max_batch_size]
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
                    logger.info(f"分割削除進捗: {min(i + max_batch_size, total_events)}/{total_events}")
            
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
        スケジュールデータからGoogleカレンダー予定を一括作成（バッチ処理対応）
        
        設計参照: 基本設計書.md 3.3章 create_events()仕様
        
        予定作成仕様:
        - 開始時刻: スケジュールデータの時刻
        - 終了時刻: 開始時刻+1時間（固定）
        - タイトル: 絵文字付きタイトル（main.pyで処理済み）
        - 公開設定: URLを知る人は閲覧可能
        
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
                    logger.warning(f"予定作成エラー (ID: {request_id}): {exception}")
                    failed_count += 1
                    failed_events.append(request_id)
                else:
                    created_count += 1
                    logger.debug(f"予定作成成功: {request_id} (ID: {response.get('id')})")
            
            # Google Calendar APIの制限：1000件/バッチ
            max_batch_size = 1000
            total_events = len(events_data)
            
            # 共通のイベント作成処理
            def create_event_object(event_data):
                # タイトルに絵文字を追加
                title = event_data['title']
                emoji = event_data.get('category', '')
                if emoji and emoji not in title:
                    title = f"{emoji} {title}"
                
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
                    
                    return {
                        'summary': title,
                        'description': f"原文: {event_data.get('raw_text', '')}",
                        'start': {
                            'date': event_date.isoformat(),
                        },
                        'end': {
                            'date': end_date.isoformat(),
                        },
                        'visibility': 'public',  # 公開設定
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
                    
                    # 終了時刻（開始時刻+1時間）
                    end_datetime = start_datetime + timedelta(hours=1)
                    
                    return {
                        'summary': title,
                        'description': f"原文: {event_data.get('raw_text', '')}",
                        'start': {
                            'dateTime': start_datetime.isoformat(),
                            'timeZone': 'Asia/Tokyo',
                        },
                        'end': {
                            'dateTime': end_datetime.isoformat(),
                            'timeZone': 'Asia/Tokyo',
                        },
                        'visibility': 'public',  # 公開設定
                    }
            
            # 1000件以下の場合は一括処理、それ以上の場合は分割処理
            if total_events <= max_batch_size:
                # 一括登録（通常のケース）
                batch = self.service.new_batch_http_request(callback=create_callback)
                
                for event_data in events_data:
                    try:
                        event = create_event_object(event_data)
                        batch.add(
                            self.service.events().insert(
                                calendarId=self.calendar_id,
                                body=event
                            ),
                            request_id=event_data['title']
                        )
                    except Exception as e:
                        logger.warning(f"イベントデータ準備エラー: {event_data.get('title', 'Unknown')} - {e}")
                        failed_count += 1
                        continue
                
                batch.execute()
                logger.info(f"一括登録完了: {total_events}件")
            else:
                # 1000件を超える場合のみ分割処理
                logger.info(f"大量データ検出: {total_events}件 → 分割処理開始")
                for i in range(0, total_events, max_batch_size):
                    batch_events = events_data[i:i + max_batch_size]
                    batch = self.service.new_batch_http_request(callback=create_callback)
                    
                    for event_data in batch_events:
                        try:
                            event = create_event_object(event_data)
                            batch.add(
                                self.service.events().insert(
                                    calendarId=self.calendar_id,
                                    body=event
                                ),
                                request_id=event_data['title']
                            )
                        except Exception as e:
                            logger.warning(f"イベントデータ準備エラー: {event_data.get('title', 'Unknown')} - {e}")
                            failed_count += 1
                            continue
                    
                    batch.execute()
                    logger.info(f"分割登録進捗: {min(i + max_batch_size, total_events)}/{total_events}")
            
            logger.info(f"予定作成完了: {created_count}件成功, {failed_count}件失敗")
            
            # 失敗したイベントがある場合は警告
            if failed_events:
                logger.warning(f"作成に失敗したイベント: {', '.join(failed_events[:5])}{'...' if len(failed_events) > 5 else ''}")
            
            # 成功した件数が0より大きければ成功とする
            return created_count > 0
            
        except Exception as e:
            logger.error(f"予定作成エラー: {e}")
            return False
    
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

 