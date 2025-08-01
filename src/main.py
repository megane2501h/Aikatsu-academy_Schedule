"""
アイカツアカデミー！スケジュール同期ツール - メイン処理

アイカツアカデミー！公式サイトからスケジュール情報を取得し、
Googleカレンダーに自動同期するツールのメイン処理です。

機能:
- 公式サイトからのスケジュール自動取得
- Googleカレンダーへの同期
- 絵文字による視覚的分類
- 手動実行・自動実行の両対応
"""

import sys
import os
import argparse
import configparser
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# プロジェクト内モジュールをインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scraper import ScheduleScraper
from gcal import GoogleCalendarManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AikatsuScheduleSync:
    """
    アイカツアカデミー！スケジュール同期処理の統合管理クラス
    
    公式サイトからスケジュールを取得し、Googleカレンダーに同期する
    メイン処理を統合管理します。
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
        
        # 各モジュールの初期化
        self.scraper = ScheduleScraper(config_path)
        self.gcal_manager = GoogleCalendarManager(config_path)
        
        # 設定値の読み込み
        self.update_interval_hours = self.config.getint('Sync', 'update_interval_hours', 
                                                       fallback=6)
        
        # 古い絵文字設定は不要（scraper.pyで処理済み）
    
    def sync_schedule(self) -> bool:
        """
        スケジュール同期の実行
        
        シンプルな削除→追加方式で確実な同期を実現
        
        Returns:
            bool: 同期成功時True, 失敗時False
        """
        try:
            logger.info("=== スケジュール同期開始 ===")
            
            # 0. 設定値の検証
            if not self._validate_config():
                logger.error("設定値の検証に失敗しました")
                return False
            
            # 1. Google Calendar API認証
            logger.info("Google Calendar API認証中...")
            if not self.gcal_manager.authenticate():
                logger.error("Google Calendar API認証に失敗しました")
                logger.error("🔧 解決方法:")
                logger.error("  1. 最も可能性の高い原因: トークンの有効期限切れ")
                logger.error("  2. ローカルで新しいトークンを生成:")
                logger.error("     python src/main.py --manual --config ../config.ini")
                logger.error("  3. 生成されたtoken.jsonの内容をGitHubのsecretsに設定:")
                logger.error("     Repository Settings > Secrets > GOOGLE_TOKEN を更新")
                logger.error("  4. 必要に応じてGOOGLE_CREDENTIALSとCALENDAR_IDも確認")
                logger.error("  5. スクレーピング機能のテスト: python utils/scrape_only.py")
                return False
            
            # 2. スケジュール取得
            logger.info("公式サイトからスケジュール取得中...")
            schedule_data = self.scraper.fetch_schedule()
            if not schedule_data:
                logger.warning("取得できるスケジュールがありません")
                return True  # エラーではないので成功とする
            
            # 3. シンプルな削除→追加同期
            logger.info("シンプル同期方式: 削除→追加")
            
            # 3-1. 既存予定の削除
            start_date, end_date = self.gcal_manager._calculate_date_range(schedule_data)
            logger.info(f"既存予定削除中: {start_date.date()} ～ {end_date.date()}")
            if not self.gcal_manager.clear_events(start_date, end_date):
                logger.error("既存予定の削除に失敗しました")
                return False
            
            # 3-2. 新規予定の追加
            logger.info(f"新規予定登録中: {len(schedule_data)}件")
            if not self.gcal_manager.create_events(schedule_data):
                logger.error("新規予定の登録に失敗しました")
                return False
            
            logger.info("=== スケジュール同期完了 ===")
            return True
            
        except Exception as e:
            logger.error(f"スケジュール同期エラー: {e}")
            return False
    

    
    def _validate_config(self) -> bool:
        """
        設定値の検証
        
        サンプル値や無効な設定値をチェック
        
        Returns:
            bool: 設定値が有効な場合True, 無効な場合False
        """
        try:
            # カレンダーIDの検証
            calendar_id = self.config.get('GoogleCalendar', 'calendar_id')
            
            # サンプル値の検出
            if calendar_id in ['your_calendar_id@group.calendar.google.com', '']:
                logger.error("❌ カレンダーIDがサンプル値のままです")
                logger.error("📝 config.iniを編集して正しいカレンダーIDを設定してください")
                logger.error("🔧 取得方法: https://support.google.com/calendar/answer/37103")
                return False
            
            # カレンダーIDの形式チェック
            if '@' not in calendar_id:
                logger.error("❌ カレンダーIDの形式が正しくありません")
                logger.error(f"📝 現在の設定: {calendar_id}")
                logger.error("💡 正しい形式: xxxxx@group.calendar.google.com")
                return False
            
            # 認証ファイルの存在チェック
            credentials_file = self.config.get('GoogleCalendar', 'credentials_file', fallback='credentials.json')
            if not os.path.exists(credentials_file):
                logger.error(f"❌ 認証ファイルが見つかりません: {credentials_file}")
                logger.error("📝 Google Cloud Consoleからcredentials.jsonをダウンロードしてください")
                return False
            
            logger.debug("✅ 設定値の検証完了")
            return True
            
        except Exception as e:
            logger.error(f"設定値検証エラー: {e}")
            return False
    
    def run_manual(self) -> bool:
        """
        手動実行モード
        
        一度だけスケジュール同期を実行して終了
        
        Returns:
            bool: 実行成功時True, 失敗時False
        """
        logger.info("手動実行モードで開始")
        result = self.sync_schedule()
        
        if result:
            logger.info("手動実行完了")
        else:
            logger.error("手動実行失敗")
        
        return result
    
    def run_automatic(self) -> None:
        """
        自動実行モード
        
        設計参照: 基本設計書.md 3.4章 自動実行制御
        
        実行仕様:
        - UPDATE_INTERVAL_HOURS間隔での定期実行
        - プロセス常駐型（schedule.run_continuously）
        - エラー時も実行継続（個別処理での例外キャッチ）
        """
        logger.info(f"自動実行モードで開始（{self.update_interval_hours}時間間隔）")
        
        # スケジュール設定
        schedule.every(self.update_interval_hours).hours.do(self._scheduled_sync)
        
        # 初回実行
        logger.info("初回同期を実行")
        self._scheduled_sync()
        
        # 定期実行ループ
        logger.info("定期実行開始...")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
        except KeyboardInterrupt:
            logger.info("ユーザーによる中断")
        except Exception as e:
            logger.error(f"自動実行エラー: {e}")
    
    def _scheduled_sync(self) -> None:
        """
        スケジュール実行用のラッパー関数
        
        エラーが発生しても次回実行に影響しないよう例外をキャッチ
        """
        try:
            self.sync_schedule()
        except Exception as e:
            logger.error(f"定期実行中にエラーが発生: {e}")


def create_sample_config() -> None:
    """
    テンプレートから設定ファイルを作成
    
    config.ini.templateをコピーしてconfig.iniを生成
    """
    import shutil
    
    template_path = 'config.ini.template'
    config_path = 'config.ini'
    
    # テンプレートファイルの存在確認
    if not os.path.exists(template_path):
        logger.error(f"❌ テンプレートファイルが見つかりません: {template_path}")
        print("エラー: config.ini.template が見つかりません")
        return
    
    # 既存ファイルの確認
    if os.path.exists(config_path):
        print(f"⚠️  設定ファイル '{config_path}' は既に存在します")
        response = input("上書きしますか？ [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("キャンセルしました")
            return
    
    try:
        # テンプレートをコピー
        shutil.copy2(template_path, config_path)
        print(f"✅ 設定ファイル '{config_path}' を作成しました")
        print("📝 以下の設定を編集してください:")
        print("   - [GoogleCalendar] calendar_id: 実際のGoogleカレンダーID")
        print("   - その他の設定も必要に応じて調整")
        print("🔧 カレンダーID取得方法: https://support.google.com/calendar/answer/37103")
        
    except Exception as e:
        logger.error(f"設定ファイル作成エラー: {e}")
        print(f"エラー: 設定ファイルの作成に失敗しました - {e}")


def main():
    """
    メイン関数 - コマンドライン引数処理と実行制御
    
    設計参照: 基本設計書.md 3.4章 実行制御
    """
    parser = argparse.ArgumentParser(
        description='アイカツアカデミー！スケジュール同期ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py --manual           手動実行（一度だけ同期）
  python main.py --auto             自動実行（定期同期）
  python main.py --create-config    サンプル設定ファイル作成
        """
    )
    
    parser.add_argument('--manual', action='store_true',
                       help='手動実行モード（一度だけ同期を実行）')
    parser.add_argument('--auto', action='store_true',
                       help='自動実行モード（定期的に同期を実行）')
    parser.add_argument('--create-config', action='store_true',
                       help='サンプル設定ファイルを作成')
    parser.add_argument('--config', default='config.ini',
                       help='設定ファイルのパス（デフォルト: config.ini）')
    
    args = parser.parse_args()
    
    # サンプル設定ファイル作成
    if args.create_config:
        create_sample_config()
        return
    
    # 設定ファイルの存在確認
    if not os.path.exists(args.config):
        print(f"エラー: 設定ファイル '{args.config}' が見つかりません")
        print("--create-config オプションでサンプルファイルを作成できます")
        sys.exit(1)
    
    # アプリケーション初期化
    app = AikatsuScheduleSync(args.config)
    
    # 実行モード判定
    if args.manual:
        # 手動実行
        success = app.run_manual()
        sys.exit(0 if success else 1)
    elif args.auto:
        # 自動実行
        app.run_automatic()
    else:
        # 引数なしの場合はヘルプ表示
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main() 