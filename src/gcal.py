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
        指定期間のカレンダー予定をすべて削除
        
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
            deleted_count = 0
            
            # 各予定を削除
            for event in events:
                try:
                    self.service.events().delete(
                        calendarId=self.calendar_id,
                        eventId=event['id']
                    ).execute()
                    deleted_count += 1
                except HttpError as e:
                    logger.warning(f"予定削除エラー (ID: {event.get('id')}): {e}")
                    continue
            
            logger.info(f"既存予定削除完了: {deleted_count}件")
            return True
            
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
        スケジュールデータからGoogleカレンダー予定を一括作成
        
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
            
            for event_data in events_data:
                try:
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
                        
                        # Google Calendar予定オブジェクト作成（終日予定）
                        event = {
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
                        
                        # Google Calendar予定オブジェクト作成（時刻指定予定）
                        event = {
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
                    
                    # 予定作成
                    created_event = self.service.events().insert(
                        calendarId=self.calendar_id,
                        body=event
                    ).execute()
                    
                    created_count += 1
                    logger.debug(f"予定作成: {event_data['title']} (ID: {created_event.get('id')})")
                    
                except Exception as e:
                    logger.warning(f"個別予定作成エラー: {event_data.get('title', 'Unknown')} - {e}")
                    continue
            
            logger.info(f"予定作成完了: {created_count}件")
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

 