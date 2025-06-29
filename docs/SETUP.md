# セットアップ手順

## 1. 事前準備

### 必要なもの
- Python 3.8以上
- Googleアカウント

### 依存関係のインストール
```bash
uv sync
```

## 2. Google Calendar API設定

### 2.1 Google Cloud Consoleでプロジェクト作成
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（プロジェクト名は任意）

### 2.2 Calendar APIの有効化
1. APIとサービス > ライブラリ
2. "Google Calendar API"を検索
3. 有効にする

### 2.3 OAuth認証情報の作成
1. APIとサービス > 認証情報
2. 認証情報を作成 > OAuth クライアントID
3. アプリケーションの種類: デスクトップアプリケーション
4. 作成後、JSONファイルをダウンロード
5. ファイル名を`credentials.json`に変更してプロジェクトルートに配置

## 3. Googleカレンダーの準備

### 3.1 専用カレンダーの作成（推奨）
1. [Google Calendar](https://calendar.google.com/)にアクセス
2. 左側の「他のカレンダー」の+マークをクリック
3. 「新しいカレンダーを作成」
4. 名前を「アイカツアカデミー！」など分かりやすい名前に設定

### 3.2 カレンダーIDの取得
1. 作成したカレンダーの設定を開く
2. 「カレンダーの統合」セクション
3. カレンダーIDをコピー（example@group.calendar.google.com の形式）

## 4. 設定ファイルの作成

```bash
python src/main.py --create-config
```

`config.ini`が作成されるので、以下を編集：

```ini
[GoogleCalendar]
CALENDAR_ID = your_calendar_id@group.calendar.google.com
```

## 5. 初回実行・認証

```bash
python src/main.py --manual
```

初回実行時、ブラウザが開いてGoogleアカウントの認証が求められます。
認証後、`token.json`が自動生成されます。

## 6. 動作確認

実行後、指定したGoogleカレンダーにスケジュールが同期されていることを確認してください。

## 7. 定期実行（オプション）

### Windows（タスクスケジューラ）
1. タスクスケジューラを開く
2. 基本タスクの作成
3. 実行プログラム: `python`
4. 引数: `src/main.py --auto`
5. 開始フォルダ: プロジェクトフォルダのパス

### GitHub Actions
`.github/workflows/sync.yml`が既に用意されています。
リポジトリのSecretsに認証情報を設定してください。 