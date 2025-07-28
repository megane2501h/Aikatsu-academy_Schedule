@echo off
chcp 65001 >nul

echo.
echo ========================================
echo  Google Calendar API トークン更新ツール
echo ========================================
echo.

:: 現在のディレクトリを確認
echo 現在のディレクトリ: %CD%
echo.

:: 設定ファイルの存在確認
if not exist "config.ini" (
    echo ERROR: config.ini が見つかりません
    echo プロジェクトのルートディレクトリで実行してください
    pause
    exit /b 1
)

echo 設定ファイルを確認しました: config.ini
echo.

:: 既存のトークンファイルの確認
if exist "token.json" (
    echo 既存のトークンファイルを確認しました
    for %%A in (token.json) do echo ファイルサイズ: %%~zA bytes
    echo.
) else (
    echo 既存のトークンファイルは見つかりませんでした（初回実行）
    echo.
)

:: トークン更新の実行
echo Google Calendar API トークンを更新中...
echo 実行コマンド: python src/main.py --manual --config config.ini
echo.

python src/main.py --manual --config config.ini

if %ERRORLEVEL% neq 0 (
    echo.
    echo トークン更新に失敗しました
    echo トラブルシューティング:
    echo   1. インターネット接続を確認
    echo   2. Googleアカウントの認証を確認
    echo   3. config.ini の設定を確認
    echo.
    pause
    exit /b 1
)

echo.
echo トークン更新が完了しました
echo.

:: 新しいトークンファイルの確認
if not exist "token.json" (
    echo 新しいトークンファイルが生成されませんでした
    pause
    exit /b 1
)

echo 新しいトークンファイルを確認しました
for %%A in (token.json) do echo ファイルサイズ: %%~zA bytes
echo.

:: トークン内容の表示（機密情報は除外）
echo トークン情報（デバッグ用）:
python -c "import json; data=json.load(open('token.json')); print('有効期限:', data.get('expiry', '不明')); print('スコープ:', len(data.get('scopes', [])), '個'); print('リフレッシュトークン:', 'あり' if data.get('refresh_token') else 'なし')"
echo.

:: GitHub Secrets更新のガイダンス
echo ========================================
echo  GitHub Secrets 更新手順
echo ========================================
echo.
echo 以下の手順でGitHub Secretsを更新してください:
echo.
echo 1. GitHubリポジトリページにアクセス
echo    https://github.com/megane2501h/Aikatsu-academy_Schedule
echo.
echo 2. Settings > Secrets and variables > Actions
echo.
echo 3. GOOGLE_TOKEN を選択して「Update」をクリック
echo.
echo 4. 以下の内容をコピーして貼り付け:
echo.

:: トークンファイルの内容を表示
echo 新しいトークン内容（これをコピーしてください）:
echo ----------------------------------------
type token.json
echo ----------------------------------------
echo.

:: 自動コピー機能（Windows 10以降）
echo 自動コピー機能を試行中...
python -c "
import json
import subprocess
try:
    with open('token.json', 'r', encoding='utf-8') as f:
        token_content = f.read()
    subprocess.run(['clip'], input=token_content.encode('utf-8'), check=True)
    print('トークン内容をクリップボードにコピーしました')
    print('直接GitHub Secretsに貼り付けてください')
except Exception as e:
    print('自動コピーに失敗しました')
    print('上記の内容を手動でコピーしてください')
"
echo.

:: 完了メッセージ
echo ========================================
echo  トークン更新完了
echo ========================================
echo.
echo 次のステップ:
echo   1. 上記のトークン内容をGitHub Secretsに設定
echo   2. GitHub Actionsで同期テストを実行
echo   3. 問題が解決したことを確認
echo.
echo ヒント:
echo   - サービスアカウント認証への移行も検討してください
echo   - docs/SERVICE_ACCOUNT_SETUP.md を参照
echo.

pause 