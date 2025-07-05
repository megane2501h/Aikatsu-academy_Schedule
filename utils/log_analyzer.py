"""
GitHub Actions ログ分析ツール

実行時間の分析とボトルネック特定、最適化提案を行います。
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogAnalyzer:
    """GitHub Actionsログの分析クラス"""
    
    def __init__(self):
        """初期化"""
        self.phase_patterns = {
            'scraping': [
                r'公式サイトからスケジュール取得中',
                r'スケジュールデータ取得成功'
            ],
            'deletion': [
                r'重複防止のため事前削除を実行',
                r'既存予定削除完了'
            ],
            'creation': [
                r'差分同期開始',
                r'差分同期完了'
            ]
        }
    
    def parse_log(self, log_content: str) -> List[Dict[str, Any]]:
        """
        ログからエントリを解析
        
        Args:
            log_content: ログの内容
            
        Returns:
            List[Dict]: 解析されたログエントリ
        """
        entries = []
        lines = log_content.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # タイムスタンプの抽出
            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)', line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                try:
                    # ISO形式のタイムスタンプを解析
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    entries.append({
                        'timestamp': timestamp,
                        'raw_line': line,
                        'message': line[len(timestamp_str):].strip()
                    })
                except ValueError:
                    logger.warning(f"タイムスタンプの解析に失敗: {timestamp_str}")
                    continue
        
        return entries
    
    def identify_phases(self, log_content: str) -> Dict[str, Dict[str, Any]]:
        """
        処理フェーズの特定と時間計算
        
        Args:
            log_content: ログの内容
            
        Returns:
            Dict: 各フェーズの情報
        """
        entries = self.parse_log(log_content)
        phases = {}
        
        for phase_name, patterns in self.phase_patterns.items():
            start_time = None
            end_time = None
            
            for entry in entries:
                message = entry['message']
                
                # 開始パターンの検出
                if any(re.search(pattern, message) for pattern in patterns[:1]):
                    start_time = entry['timestamp']
                
                # 終了パターンの検出
                if any(re.search(pattern, message) for pattern in patterns[-1:]):
                    end_time = entry['timestamp']
            
            # フェーズ情報の計算
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
                phases[phase_name] = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'start_time_str': start_time.strftime('%H:%M:%S'),
                    'end_time_str': end_time.strftime('%H:%M:%S')
                }
        
        return phases
    
    def identify_bottlenecks(self, log_content: str) -> Dict[str, Dict[str, Any]]:
        """
        ボトルネックの特定
        
        Args:
            log_content: ログの内容
            
        Returns:
            Dict: ボトルネック情報
        """
        phases = self.identify_phases(log_content)
        bottlenecks = {}
        
        # 閾値を設定（2秒以上をボトルネックとする）
        threshold = 2.0
        
        for phase_name, phase_info in phases.items():
            if phase_info['duration'] > threshold:
                bottlenecks[phase_name] = phase_info
        
        return bottlenecks
    
    def get_sorted_bottlenecks(self, log_content: str) -> List[Dict[str, Any]]:
        """
        ボトルネックを時間順でソート
        
        Args:
            log_content: ログの内容
            
        Returns:
            List[Dict]: ソートされたボトルネック情報
        """
        bottlenecks = self.identify_bottlenecks(log_content)
        
        sorted_bottlenecks = []
        for phase_name, phase_info in bottlenecks.items():
            sorted_bottlenecks.append({
                'phase': phase_name,
                'duration': phase_info['duration'],
                'start_time': phase_info['start_time'],
                'end_time': phase_info['end_time']
            })
        
        # 時間の長い順にソート
        sorted_bottlenecks.sort(key=lambda x: x['duration'], reverse=True)
        
        return sorted_bottlenecks
    
    def generate_optimization_suggestions(self, log_content: str) -> List[Dict[str, Any]]:
        """
        最適化提案の生成
        
        Args:
            log_content: ログの内容
            
        Returns:
            List[Dict]: 最適化提案
        """
        phases = self.identify_phases(log_content)
        suggestions = []
        
        # 削除処理の最適化提案
        if 'deletion' in phases and phases['deletion']['duration'] > 3.0:
            suggestions.append({
                'phase': 'deletion',
                'current_time': phases['deletion']['duration'],
                'priority': 'high',
                'title': '既存予定削除処理の最適化',
                'description': '一括削除処理をバッチ処理に変更することで時間短縮が期待できます',
                'estimated_improvement': phases['deletion']['duration'] * 0.6,  # 60%削減
                'implementation': [
                    'Google Calendar API のバッチリクエストを使用',
                    '削除対象の事前フィルタリング強化',
                    '並列処理の導入'
                ]
            })
        
        # スクレイピング処理の最適化提案
        if 'scraping' in phases and phases['scraping']['duration'] > 2.0:
            suggestions.append({
                'phase': 'scraping',
                'current_time': phases['scraping']['duration'],
                'priority': 'medium',
                'title': 'スクレイピング処理の最適化',
                'description': 'HTTPリクエストの最適化とキャッシュ機能で高速化',
                'estimated_improvement': phases['scraping']['duration'] * 0.3,  # 30%削減
                'implementation': [
                    'HTTPセッションの再利用',
                    'レスポンスキャッシュの導入',
                    'リクエスト並列化'
                ]
            })
        
        # 作成処理の最適化提案
        if 'creation' in phases and phases['creation']['duration'] > 2.0:
            suggestions.append({
                'phase': 'creation',
                'current_time': phases['creation']['duration'],
                'priority': 'medium',
                'title': '予定作成処理の最適化',
                'description': 'バッチ作成処理の効率化',
                'estimated_improvement': phases['creation']['duration'] * 0.4,  # 40%削減
                'implementation': [
                    'バッチサイズの最適化',
                    'エラーハンドリングの改善',
                    'リトライ機能の最適化'
                ]
            })
        
        return suggestions
    
    def estimate_time_savings(self, log_content: str) -> Dict[str, float]:
        """
        時間短縮の推定
        
        Args:
            log_content: ログの内容
            
        Returns:
            Dict: 時間短縮の推定値
        """
        phases = self.identify_phases(log_content)
        suggestions = self.generate_optimization_suggestions(log_content)
        
        current_total = sum(phase['duration'] for phase in phases.values())
        estimated_savings = sum(suggestion['estimated_improvement'] for suggestion in suggestions)
        estimated_total = current_total - estimated_savings
        
        return {
            'current_total': current_total,
            'estimated_total': max(estimated_total, 1.0),  # 最低1秒は保証
            'time_saved': estimated_savings,
            'improvement_percentage': (estimated_savings / current_total) * 100 if current_total > 0 else 0
        }
    
    def generate_report(self, log_content: str, output_format: str = 'text') -> str:
        """
        分析レポートの生成
        
        Args:
            log_content: ログの内容
            output_format: 出力形式（text, json, markdown）
            
        Returns:
            str: 分析レポート
        """
        phases = self.identify_phases(log_content)
        bottlenecks = self.get_sorted_bottlenecks(log_content)
        suggestions = self.generate_optimization_suggestions(log_content)
        time_savings = self.estimate_time_savings(log_content)
        
        if output_format == 'json':
            return json.dumps({
                'phases': phases,
                'bottlenecks': bottlenecks,
                'suggestions': suggestions,
                'time_savings': time_savings
            }, indent=2, default=str)
        
        elif output_format == 'markdown':
            return self._generate_markdown_report(phases, bottlenecks, suggestions, time_savings)
        
        else:  # text
            return self._generate_text_report(phases, bottlenecks, suggestions, time_savings)
    
    def _generate_text_report(self, phases: Dict, bottlenecks: List, suggestions: List, time_savings: Dict) -> str:
        """テキスト形式のレポート生成"""
        report = []
        report.append("=== GitHub Actions 実行時間分析レポート ===\n")
        
        # 処理フェーズ別時間
        report.append("📊 処理フェーズ別実行時間:")
        for phase_name, phase_info in phases.items():
            report.append(f"  {phase_name}: {phase_info['duration']:.2f}秒 ({phase_info['start_time_str']} - {phase_info['end_time_str']})")
        
        # ボトルネック
        report.append("\n🔍 ボトルネック（時間の長い順）:")
        for i, bottleneck in enumerate(bottlenecks, 1):
            report.append(f"  {i}. {bottleneck['phase']}: {bottleneck['duration']:.2f}秒")
        
        # 最適化提案
        report.append("\n💡 最適化提案:")
        for i, suggestion in enumerate(suggestions, 1):
            report.append(f"  {i}. {suggestion['title']} ({suggestion['priority']})")
            report.append(f"     現在: {suggestion['current_time']:.2f}秒")
            report.append(f"     改善見込み: {suggestion['estimated_improvement']:.2f}秒削減")
            report.append(f"     実装方法: {', '.join(suggestion['implementation'])}")
        
        # 時間短縮推定
        report.append("\n⚡ 時間短縮推定:")
        report.append(f"  現在の実行時間: {time_savings['current_total']:.2f}秒")
        report.append(f"  最適化後予想時間: {time_savings['estimated_total']:.2f}秒")
        report.append(f"  短縮時間: {time_savings['time_saved']:.2f}秒 ({time_savings['improvement_percentage']:.1f}%改善)")
        
        return "\n".join(report)
    
    def _generate_markdown_report(self, phases: Dict, bottlenecks: List, suggestions: List, time_savings: Dict) -> str:
        """Markdown形式のレポート生成"""
        report = []
        report.append("# GitHub Actions 実行時間分析レポート\n")
        
        report.append("## 📊 処理フェーズ別実行時間\n")
        report.append("| フェーズ | 実行時間 | 開始時刻 | 終了時刻 |")
        report.append("|----------|----------|----------|----------|")
        for phase_name, phase_info in phases.items():
            report.append(f"| {phase_name} | {phase_info['duration']:.2f}秒 | {phase_info['start_time_str']} | {phase_info['end_time_str']} |")
        
        report.append("\n## 🔍 ボトルネック分析\n")
        for i, bottleneck in enumerate(bottlenecks, 1):
            report.append(f"{i}. **{bottleneck['phase']}**: {bottleneck['duration']:.2f}秒")
        
        report.append("\n## 💡 最適化提案\n")
        for i, suggestion in enumerate(suggestions, 1):
            report.append(f"### {i}. {suggestion['title']} ({suggestion['priority']})")
            report.append(f"- **現在の実行時間**: {suggestion['current_time']:.2f}秒")
            report.append(f"- **改善見込み**: {suggestion['estimated_improvement']:.2f}秒削減")
            report.append(f"- **実装方法**:")
            for impl in suggestion['implementation']:
                report.append(f"  - {impl}")
            report.append("")
        
        report.append("## ⚡ 時間短縮推定\n")
        report.append(f"- **現在の実行時間**: {time_savings['current_total']:.2f}秒")
        report.append(f"- **最適化後予想時間**: {time_savings['estimated_total']:.2f}秒")
        report.append(f"- **短縮時間**: {time_savings['time_saved']:.2f}秒 ({time_savings['improvement_percentage']:.1f}%改善)")
        
        return "\n".join(report)


def main():
    """メイン関数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python log_analyzer.py <ログファイル> [出力形式]")
        print("出力形式: text, json, markdown (デフォルト: text)")
        sys.exit(1)
    
    log_file = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'text'
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        analyzer = LogAnalyzer()
        report = analyzer.generate_report(log_content, output_format)
        print(report)
        
    except FileNotFoundError:
        print(f"エラー: ファイル '{log_file}' が見つかりません")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 