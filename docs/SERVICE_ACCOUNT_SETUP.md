# Google Calendar API サービスアカウント認証設定ガイド

サービスアカウント認証により、トークンの期限切れを根本的に解決し、完全自動化を実現します。

## 🎯 メリット

- ✅ **期限切れなし**: サービスアカウントキーは長期有効
- ✅ **完全自動化**: 人の介入不要
- ✅ **企業レベル**: Google推奨の本格運用方式
- ✅ **セキュア**: OAuth2より安全な認証方式

## 📋 設定手順

### 1️⃣ Google Cloud Console設定

1. **Google Cloud Console**にアクセス: https://console.cloud.google.com/
2. プロジェクトを選択（または新規作成）
3. **APIとサービス** > **認証情報**に移動
4. **認証情報を作成** > **サービスアカウント**を選択

### 2️⃣ サービスアカウント作成

```
サービスアカウント名: aikatsu-schedule-bot
説明: アイカツアカデミー！スケジュール自動同期用
```

### 3️⃣ キーファイル生成

1. 作成したサービスアカウントをクリック
2. **キー**タブに移動
3. **鍵を追加** > **新しい鍵を作成**
4. **JSON**形式を選択してダウンロード
5. ファイル名を`service-account.json`に変更

### 4️⃣ カレンダー共有設定

1. **Google Calendar**を開く
2. 対象カレンダーの**設定と共有**
3. **特定のユーザーと共有**
4. サービスアカウントのメールアドレスを追加
5. 権限を**予定の変更および管理**に設定

### 5️⃣ GitHub Secrets設定

```bash
# service-account.jsonの内容をコピー
cat service-account.json | pbcopy  # macOS
cat service-account.json | clip    # Windows
```

GitHub Settings > Secrets and variables > Actions:
- `GOOGLE_SERVICE_ACCOUNT_JSON`: JSONファイル全体の内容

## 🔧 実装仕様

### config.ini設定
```ini
[GoogleCalendar]
auth_method = service_account
service_account_file = ../service-account.json
calendar_id = your-calendar-id@group.calendar.google.com
```

### 認証ロジック変更点
- OAuth2認証を廃止
- サービスアカウント認証に統一
- トークンリフレッシュ処理を削除

## 🚀 移行の利点

- **運用コスト**: 月次手動作業 → 完全無人
- **安定性**: トークン期限切れエラー → ゼロ
- **保守性**: 複雑な認証フロー → シンプル
- **スケーラビリティ**: 個人用 → 企業レベル

## ⚠️ 注意事項

- サービスアカウントキーは**機密情報**として厳重管理
- GitHub Secretsで暗号化保存
- 定期的なキーローテーション推奨（年1回） 