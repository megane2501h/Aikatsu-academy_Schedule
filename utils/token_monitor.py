#!/usr/bin/env python3
"""
Google Calendar APIトークン期限監視ユーティリティ

OAuth2トークンの有効期限を監視し、期限切れ前に
アラートを送信する機能を提供します。

機能:
- トークン有効期限の確認
- 期限切れ予告通知
- 自動更新の提案
- GitHub Actions通知の送信
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import configparser

# プロジェクト内モジュールをインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TokenMonitor:
    """
    Google Calendar APIトークンの期限監視クラス
    
    OAuth2トークンの有効期限を監視し、適切なタイミングで
    アラートや更新提案を行います。
    """
    
    def __init__(self, config_path: str = "config.ini"):
        """
        初期化処理
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        # 設定値の読み込み
        self.token_file = self.config.get('GoogleCalendar', 'token_file', 
                                         fallback='token.json')
        self.auth_method = self.config.get('GoogleCalendar', 'auth_method', 
                                          fallback='oauth2')
        
        # アラート設定（デフォルト：3日前、1日前、当日）
        self.alert_days = [3, 1, 0]
    
    def check_token_expiry(self) -> Dict[str, Any]:
        """
        トークンの有効期限を確認
        
        Returns:
            Dict: トークン状態情報
        """
        try:
            # サービスアカウント認証の場合はチェック不要
            if self.auth_method == 'service_account':
                return {
                    'status': 'service_account',
                    'message': 'サービスアカウント認証: 期限切れの心配なし',
                    'needs_renewal': False,
                    'days_until_expiry': None
                }
            
            # OAuth2トークンファイルの確認
            if not os.path.exists(self.token_file):
                return {
                    'status': 'missing',
                    'message': 'トークンファイルが見つかりません',
                    'needs_renewal': True,
                    'days_until_expiry': None
                }
            
            # トークンファイルの読み込み
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
            except Exception as e:
                return {
                    'status': 'corrupted',
                    'message': f'トークンファイルの読み込みエラー: {e}',
                    'needs_renewal': True,
                    'days_until_expiry': None
                }
            
            # 有効期限の確認
            if 'expiry' not in token_data:
                return {
                    'status': 'no_expiry',
                    'message': '有効期限情報が見つかりません',
                    'needs_renewal': True,
                    'days_until_expiry': None
                }
            
            # 有効期限の解析
            try:
                expiry_str = token_data['expiry']
                # RFC3339形式の日時文字列を解析
                if expiry_str.endswith('Z'):
                    expiry_str = expiry_str[:-1] + '+00:00'
                
                expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                # タイムゾーンを除去して比較
                if expiry_time.tzinfo:
                    expiry_time = expiry_time.replace(tzinfo=None)
                
                now = datetime.utcnow()
                time_diff = expiry_time - now
                days_until_expiry = time_diff.days
                
                # 状態の判定
                if days_until_expiry < 0:
                    status = 'expired'
                    message = f'トークンは既に期限切れです (期限: {expiry_time})'
                    needs_renewal = True
                elif days_until_expiry in self.alert_days:
                    status = 'warning'
                    message = f'トークンが{days_until_expiry}日後に期限切れになります (期限: {expiry_time})'
                    needs_renewal = True
                else:
                    status = 'valid'
                    message = f'トークンは有効です (残り: {days_until_expiry}日)'
                    needs_renewal = False
                
                return {
                    'status': status,
                    'message': message,
                    'needs_renewal': needs_renewal,
                    'days_until_expiry': days_until_expiry,
                    'expiry_time': expiry_time.isoformat()
                }
                
            except Exception as e:
                return {
                    'status': 'parse_error',
                    'message': f'有効期限の解析エラー: {e}',
                    'needs_renewal': True,
                    'days_until_expiry': None
                }
                
        except Exception as e:
            logger.error(f"トークン監視エラー: {e}")
            return {
                'status': 'error',
                'message': f'監視処理エラー: {e}',
                'needs_renewal': True,
                'days_until_expiry': None
            }
    
    def send_notification(self, token_info: Dict[str, Any]) -> bool:
        """
        トークン状態の通知を送信
        
        Args:
            token_info: check_token_expiry()の結果
            
        Returns:
            bool: 通知送信成功時True
        """
        try:
            status = token_info['status']
            message = token_info['message']
            needs_renewal = token_info['needs_renewal']
            
            # ログ出力
            if status == 'expired':
                logger.error(f"🚨 {message}")
            elif status == 'warning':
                logger.warning(f"⚠️  {message}")
            elif status == 'valid':
                logger.info(f"✅ {message}")
            else:
                logger.info(f"ℹ️  {message}")
            
            # 更新が必要な場合のガイダンス
            if needs_renewal:
                logger.info("🔧 トークン更新方法:")
                logger.info("  1. ローカル環境で認証し直し:")
                logger.info("     python src/main.py --manual --config config.ini")
                logger.info("  2. GitHub Secretsを更新:")
                logger.info("     GOOGLE_TOKEN -> 新しいtoken.jsonの内容")
                logger.info("  3. または、サービスアカウント認証への移行を検討:")
                logger.info("     docs/SERVICE_ACCOUNT_SETUP.md を参照")
                
                # GitHub Actions環境での追加通知
                if os.getenv('GITHUB_ACTIONS') == 'true':
                    logger.error("GitHub Actions環境でトークン更新が必要です")
                    logger.error("手動でsecretsを更新してください")
            
            return True
            
        except Exception as e:
            logger.error(f"通知送信エラー: {e}")
            return False
    
    def monitor_and_notify(self) -> Dict[str, Any]:
        """
        トークン監視と通知の統合処理
        
        Returns:
            Dict: 処理結果
        """
        logger.info("=== Google Calendar APIトークン監視開始 ===")
        
        # トークン状態確認
        token_info = self.check_token_expiry()
        
        # 通知送信
        notification_sent = self.send_notification(token_info)
        
        # 結果の統合
        result = {
            'token_info': token_info,
            'notification_sent': notification_sent,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("=== トークン監視完了 ===")
        return result


def main():
    """
    スタンドアロン実行用のメイン関数
    """
    try:
        # 設定ファイルのパスを決定
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini.template')
        
        if not os.path.exists(config_path):
            logger.error("設定ファイルが見つかりません")
            sys.exit(1)
        
        # トークン監視実行
        monitor = TokenMonitor(config_path)
        result = monitor.monitor_and_notify()
        
        # 結果に応じた終了コード
        if result['token_info']['needs_renewal']:
            sys.exit(1)  # 更新が必要な場合は異常終了
        else:
            sys.exit(0)  # 正常終了
            
    except Exception as e:
        logger.error(f"トークン監視の実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 