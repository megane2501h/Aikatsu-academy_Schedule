# Google Calendar API認証自動化 - 移行ガイド

Google Calendar APIの認証自動化を実現するための **ベストプラクティス** と段階的移行手順を説明します。

## 🎯 自動化レベルの選択

### レベル1: 改善されたOAuth2（短期解決）
- **適用期間**: 1-3ヶ月の短期運用
- **設定難易度**: ⭐⭐☆☆☆（簡単）
- **メンテナンス**: 月1回程度のトークン更新

### レベル2: サービスアカウント認証（推奨）
- **適用期間**: 長期運用（年単位）
- **設定難易度**: ⭐⭐⭐☆☆（中程度）
- **メンテナンス**: 年1回のキー更新

### レベル3: ハイブリッド（最高水準）
- **適用期間**: エンタープライズレベル
- **設定難易度**: ⭐⭐⭐⭐☆（高度）
- **メンテナンス**: ほぼ無人運用

## 🚀 推奨移行パス

### Phase 1: 即座実行（今すぐ）
**目的**: 現在のトークン期限切れ問題を解決

```bash
# 1. 現在のトークンを更新
python src/main.py --manual --config config.ini

# 2. GitHub Secretsを更新
# Repository Settings > Secrets > GOOGLE_TOKEN
```

### Phase 2: 短期改善（1週間以内）
**目的**: 自動リフレッシュ機能の活用

```bash
# 1. 改善されたリフレッシュ機能をテスト
git pull origin main  # 最新の改善を取得

# 2. トークン監視機能を実行
python utils/token_monitor.py

# 3. 定期監視の設定
# GitHub Actions で週1回のトークンチェック
```

### Phase 3: 長期解決（2週間以内）
**目的**: サービスアカウント認証への完全移行

```bash
# 1. サービスアカウントの作成
# docs/SERVICE_ACCOUNT_SETUP.md の手順に従う

# 2. 新しいワークフローでテスト
# .github/workflows/sync-service-account.yml を使用

# 3. 本格運用開始
# 従来のOAuth2ワークフローを無効化
```

## 📊 選択基準マトリックス

| 要件 | OAuth2改善 | サービスアカウント | ハイブリッド |
|------|------------|-------------------|-------------|
| **即座の問題解決** | ✅ | ⚠️（設定時間要） | ⚠️（設定時間要） |
| **長期安定性** | ⚠️（月次更新） | ✅ | ✅ |
| **設定の簡単さ** | ✅ | ⚠️ | ❌ |
| **メンテナンス工数** | ⚠️（高） | ✅（低） | ✅（最低） |
| **セキュリティ** | ⚠️ | ✅ | ✅ |
| **企業利用** | ❌ | ✅ | ✅ |

## 🔧 実装コマンド集

### 現在のシステム診断
```bash
# トークン状態確認
python utils/token_monitor.py

# スクレーピング機能確認
python utils/scrape_only.py

# 設定ファイル確認
cat config.ini
```

### OAuth2改善の適用
```bash
# 最新の改善を取得
git pull origin main

# 改善されたリフレッシュ機能をテスト
python src/main.py --manual --config config.ini
```

### サービスアカウント移行
```bash
# 1. 設定ファイルを更新
# config.ini で auth_method = service_account

# 2. サービスアカウントファイルを配置
# service-account.json を適切な場所に

# 3. GitHub Secretsを更新
# GOOGLE_SERVICE_ACCOUNT_JSON を追加

# 4. 新しいワークフローを実行
# Actions > サービスアカウント同期 > Run workflow
```

## 🎯 推奨決定フローチャート

```
現在のトークン期限切れ？
├── Yes → 【緊急】Phase 1実行 → Phase 2へ
└── No → 長期運用予定？
    ├── 3ヶ月未満 → OAuth2改善（Phase 2）
    ├── 6ヶ月以上 → サービスアカウント（Phase 3）
    └── 企業レベル → ハイブリッド（Phase 3+）
```

## ⚡ クイックスタート（忙しい人向け）

### 今すぐ問題解決（5分）
```bash
# トークンを即座に更新
python src/main.py --manual --config config.ini
# 生成されたtoken.jsonをGitHub Secretsに設定
```

### 根本解決（30分）
```bash
# サービスアカウント認証への移行
# 1. docs/SERVICE_ACCOUNT_SETUP.md を参照
# 2. Google Cloud Consoleで設定
# 3. .github/workflows/sync-service-account.yml を実行
```

## 💡 トラブルシューティング

### よくある問題

**Q: どの方法が一番簡単？**
A: 今すぐ → OAuth2トークン更新、長期的 → サービスアカウント

**Q: 設定が複雑で困っている**
A: OAuth2改善から始めて、段階的にサービスアカウントに移行

**Q: 企業で使いたい**
A: サービスアカウント一択。セキュリティと安定性が重要

**Q: テスト環境で確認したい**
A: utils/scrape_only.py でスクレーピング、utils/token_monitor.py で認証確認

## 📞 サポート

- **スクレーピング問題**: `python utils/scrape_only.py` で確認
- **認証問題**: `python utils/token_monitor.py` で診断
- **設定問題**: `docs/SERVICE_ACCOUNT_SETUP.md` を参照
- **GitHub Actions問題**: ワークフローログを確認

## 🎉 移行完了後の利点

### OAuth2改善後
- ✅ トークンリフレッシュの安定性向上
- ✅ エラー時の自動リトライ
- ✅ 詳細な状態監視

### サービスアカウント移行後
- ✅ **完全な無人運用**
- ✅ **トークン期限切れの撲滅**
- ✅ **企業レベルのセキュリティ**
- ✅ **年次メンテナンスのみ**

手動更新の煩わしさから解放され、真の自動化を実現できます！ 