"""
GitHub Actions ログ分析ツールのテスト

TDD方式で開発：テストファーストで機能を定義
"""

import unittest
from datetime import datetime, timedelta
import os
import sys

# 親ディレクトリからインポート
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLogAnalyzer(unittest.TestCase):
    """ログ分析ツールのテストクラス"""
    
    def setUp(self):
        """テストデータの準備"""
        self.sample_log = """
2025-07-05T10:33:37.9888353Z shell: /usr/bin/bash -e {0}
2025-07-05T10:33:39.3276522Z INFO:__main__:手動実行モードで開始
2025-07-05T10:33:39.4715536Z INFO:__main__:公式サイトからスケジュール取得中...
2025-07-05T10:33:42.4035459Z INFO:scraper:スケジュールデータ取得成功: 36件
2025-07-05T10:33:42.4201993Z INFO:__main__:🧹 GitHub Actions環境 - 重複防止のため事前削除を実行
2025-07-05T10:33:46.4910795Z INFO:gcal:既存予定削除完了: 72件成功, 0件失敗
2025-07-05T10:33:46.4911865Z INFO:gcal:差分同期開始: 36件の新規データ
2025-07-05T10:33:49.3343670Z INFO:gcal:差分同期完了
2025-07-05T10:33:49.3344539Z INFO:__main__:=== スケジュール同期完了 ===
"""
    
    def test_parse_log_timestamps(self):
        """ログからタイムスタンプを正しく抽出できるか"""
        from utils.log_analyzer import LogAnalyzer
        
        analyzer = LogAnalyzer()
        entries = analyzer.parse_log(self.sample_log)
        
        # 最初のエントリのタイムスタンプをチェック
        first_entry = entries[0]
        self.assertIsInstance(first_entry['timestamp'], datetime)
        self.assertEqual(first_entry['timestamp'].year, 2025)
        self.assertEqual(first_entry['timestamp'].month, 7)
        self.assertEqual(first_entry['timestamp'].day, 5)
    
    def test_identify_process_phases(self):
        """処理フェーズの特定ができるか"""
        from utils.log_analyzer import LogAnalyzer
        
        analyzer = LogAnalyzer()
        phases = analyzer.identify_phases(self.sample_log)
        
        # 期待される処理フェーズ
        expected_phases = ['scraping', 'deletion', 'creation']
        
        for phase in expected_phases:
            self.assertIn(phase, phases)
            self.assertIn('duration', phases[phase])
            self.assertIn('start_time', phases[phase])
            self.assertIn('end_time', phases[phase])
    
    def test_calculate_duration(self):
        """処理時間の計算が正しいか"""
        from utils.log_analyzer import LogAnalyzer
        
        analyzer = LogAnalyzer()
        phases = analyzer.identify_phases(self.sample_log)
        
        # スクレイピング処理時間（約3秒）
        scraping_duration = phases['scraping']['duration']
        self.assertGreater(scraping_duration, 2.0)
        self.assertLess(scraping_duration, 4.0)
        
        # 削除処理時間（約4秒）
        deletion_duration = phases['deletion']['duration']
        self.assertGreater(deletion_duration, 3.0)
        self.assertLess(deletion_duration, 5.0)
    
    def test_identify_bottlenecks(self):
        """ボトルネックの特定ができるか"""
        from utils.log_analyzer import LogAnalyzer
        
        analyzer = LogAnalyzer()
        bottlenecks = analyzer.identify_bottlenecks(self.sample_log)
        
        # 最も時間がかかる処理が特定されているか
        self.assertIn('deletion', bottlenecks)
        self.assertGreater(bottlenecks['deletion']['duration'], 3.0)
        
        # ボトルネックの順位付けができているか
        sorted_bottlenecks = analyzer.get_sorted_bottlenecks(self.sample_log)
        self.assertEqual(sorted_bottlenecks[0]['phase'], 'deletion')
    
    def test_generate_optimization_suggestions(self):
        """最適化提案の生成ができるか"""
        from utils.log_analyzer import LogAnalyzer
        
        analyzer = LogAnalyzer()
        suggestions = analyzer.generate_optimization_suggestions(self.sample_log)
        
        # 提案が生成されているか
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # 削除処理の最適化提案が含まれているか
        deletion_suggestions = [s for s in suggestions if 'deletion' in s['phase']]
        self.assertGreater(len(deletion_suggestions), 0)
    
    def test_estimate_improvement_time(self):
        """改善時間の推定ができるか"""
        from utils.log_analyzer import LogAnalyzer
        
        analyzer = LogAnalyzer()
        improvements = analyzer.estimate_time_savings(self.sample_log)
        
        # 改善推定値が含まれているか
        self.assertIn('current_total', improvements)
        self.assertIn('estimated_total', improvements)
        self.assertIn('time_saved', improvements)
        
        # 時間短縮が見込まれるか
        self.assertGreater(improvements['time_saved'], 0)


if __name__ == '__main__':
    unittest.main() 