# アイカツアカデミー！スケジュール同期ツール

アイカツアカデミー！公式サイトのスケジュール情報をGoogleカレンダーに自動同期するツールです。

## 🚀 セットアップ

### 1. 必要なもの
- Python 3.8以上
- Google アカウント（カレンダー作成用）

### 2. インストール

```bash
# 依存関係をインストール
uv sync
# またはpipの場合: pip install -r requirements.txt
```

### 3. Google API設定

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクト作成
2. Calendar APIを有効化  
3. OAuth 2.0認証情報を作成してcredentials.jsonをダウンロード
4. credentials.jsonをプロジェクトルートに配置

### 4. 設定ファイル作成

```bash
python src/main.py --create-config
```

config.iniのCALENDAR_IDを自分のGoogleカレンダーIDに変更してください。

### 5. 実行

```bash
# 初回実行（認証が必要）
python src/main.py --manual
```

## 📁 ファイル構成

```
├── src/                    # メインコード
│   ├── main.py            # メイン処理
│   ├── scraper.py         # スケジュール取得
│   └── gcal.py            # Googleカレンダー連携
├── utils/                  
│   └── scrape_only.py     # テスト用スクリプト
├── config.ini             # 設定ファイル
├── credentials.json       # Google API認証情報
└── token.json             # 認証トークン（自動生成）
```

## 🛠️ テスト実行

APIを使わずにスケジュール取得のみテストしたい場合：

```bash
python utils/scrape_only.py
```

結果は`output/schedule.csv`と`output/schedule.json`に出力されます。


## 🔧 トラブルシューティング

### 認証エラー
- credentials.jsonが正しく配置されているか確認
- Googleカレンダーの共有設定を確認

### スケジュール取得失敗
- ネットワーク接続を確認  
- 公式サイトが正常に動作しているか確認

### カレンダー同期失敗
- CALENDAR_IDが正しいか確認
- カレンダーへの書き込み権限があるか確認

詳細なエラー情報はログで確認できます。

## 📖 詳細ドキュメント

- [詳細セットアップ手順](docs/SETUP.md)
- [FAQ・トラブルシューティング](docs/FAQ.md) 