# よくある問題・トラブルシューティング

## 認証関連

### Q: 認証エラーが出る
**A:** 以下を確認してください：

1. `credentials.json`が正しく配置されているか
2. Google Cloud ConsoleでCalendar APIが有効になっているか
3. OAuth認証情報が正しく作成されているか

### Q: token.jsonを削除してしまった
**A:** 再度`python src/main.py --manual`を実行すれば再認証されて自動生成されます。

## カレンダー関連

### Q: カレンダーに同期されない
**A:** 以下を確認してください：

1. `config.ini`のCALENDAR_IDが正しいか
2. カレンダーの共有設定で書き込み権限があるか
3. カレンダーが削除されていないか

### Q: CALENDAR_IDがわからない
**A:** Google Calendarでカレンダー設定 > 「カレンダーの統合」からコピーできます。

### Q: 既存の予定が消えた
**A:** このツールは指定期間の予定を完全に置き換えます。専用カレンダーの使用を推奨します。

## スケジュール取得関連

### Q: スケジュールが取得できない
**A:** 以下を確認してください：

1. インターネット接続
2. 公式サイト（https://aikatsu-academy.com/schedule/）が正常に動作しているか
3. サイト構造が変更されていないか

### Q: 一部のスケジュールに絵文字がない
**A:** `config.ini`の絵文字設定を追加・調整してください。

## 実行関連

### Q: ModuleNotFoundError が出る
**A:** 依存関係のインストールを確認してください：
```bash
uv sync
```

### Q: 自動実行が動かない
**A:** 手動実行（`--manual`）で正常動作することを先に確認してください。

### Q: GitHub Actionsで失敗する
**A:** リポジトリのSecretsに認証情報が正しく設定されているか確認してください。

## エラーメッセージ別対処法

### `カレンダーが見つかりません (404)`
→ CALENDAR_IDを確認してください

### `認証情報ファイルが見つかりません`
→ credentials.jsonの配置を確認してください

### `スケジュール取得エラー`
→ ネットワーク接続と公式サイトの状態を確認してください

## サポート

解決しない場合は、GitHubのIssuesで報告してください。
その際、エラーメッセージとログを含めてください。

# FAQ - よくある質問

## Google Calendar API認証エラー

### Q: GitHub Actionsで「Token has been expired or revoked」エラーが発生する

**A: 認証トークンの有効期限が切れています。以下の手順で修正してください:**

1. **ローカルで認証し直す**
   ```bash
   # 古いトークンを削除
   rm token.json
   
   # 再認証を実行
   cd src
   python main.py --manual
   ```

2. **新しいトークンを取得**
   - 認証完了後、`token.json`ファイルが更新されます
   - このファイルの内容をコピーしてください

3. **GitHub Secretsを更新**
   - GitHub リポジトリの Settings > Secrets and variables > Actions
   - `GOOGLE_TOKEN` を新しいトークンで更新
   - `GOOGLE_CREDENTIALS` と `CALENDAR_ID` も確認

4. **動作確認**
   ```bash
   # スクレーピングのみテスト（認証不要）
   python utils/scrape_only.py
   
   # 完全テスト
   python src/main.py --manual
   ```

### Q: 設定ファイルのキーエラーが発生する

**A: 設定ファイルのキーを小文字に統一してください:**

```ini
[GoogleCalendar]
calendar_id = your_calendar_id@group.calendar.google.com
credentials_file = ../credentials.json
token_file = ../token.json

[Sync]
update_interval_hours = 6
```

### Q: 非対話的環境で認証エラーが発生する

**A: GitHub Actionsでは事前に認証されたトークンが必要です:**

1. ローカルで認証を完了させる
2. 生成されたトークンをGitHub Secretsに設定
3. GitHub Actionsは設定されたトークンを使用

### Q: スクレーピングのみテストしたい

**A: `utils/scrape_only.py`を使用してください:**

```bash
python utils/scrape_only.py
```

このスクリプトは：
- Google Calendar APIを使用しません
- 認証エラーを回避できます
- スクレーピング機能のみテストできます
- CSV/JSONファイルに結果を出力します

## トラブルシューティング

### 認証トークンの再生成手順

1. **古いトークンを削除**
   ```bash
   rm token.json
   ```

2. **Google Cloud Consoleでプロジェクトを確認**
   - OAuth 2.0 認証情報が有効か確認
   - 必要に応じて新しい認証情報を作成

3. **ローカルで再認証**
   ```bash
   python src/main.py --manual
   ```

4. **GitHub Secretsを更新**
   - 新しいトークンをコピー
   - GitHub リポジトリの Secrets を更新

### ログの確認方法

GitHub Actionsのログで以下を確認してください：

- `Google認証情報を設定中...`
- `✅ 認証ファイルを正常に設定しました`
- `ERROR:gcal:認証エラー: `

### デバッグ情報

詳細なエラー情報が必要な場合：

```bash
# デバッグモードで実行
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.main import AikatsuScheduleSync
app = AikatsuScheduleSync()
app.run_manual()
"
``` 