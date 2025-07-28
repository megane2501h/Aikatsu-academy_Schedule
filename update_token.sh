#!/bin/bash

# 文字エンコーディング設定
export LANG=ja_JP.UTF-8

echo
echo "========================================"
echo " Google Calendar API トークン更新ツール"
echo "========================================"
echo

# 現在のディレクトリを確認
echo "📍 現在のディレクトリ: $(pwd)"
echo

# 設定ファイルの存在確認
if [ ! -f "config.ini" ]; then
    echo "❌ config.ini が見つかりません"
    echo "📁 プロジェクトのルートディレクトリで実行してください"
    exit 1
fi

echo "✅ 設定ファイルを確認しました: config.ini"
echo

# 既存のトークンファイルの確認
if [ -f "token.json" ]; then
    echo "📄 既存のトークンファイルを確認しました"
    echo "📊 ファイルサイズ: $(stat -c%s token.json) bytes"
    echo
else
    echo "ℹ️  既存のトークンファイルは見つかりませんでした（初回実行）"
    echo
fi

# トークン更新の実行
echo "🔄 Google Calendar API トークンを更新中..."
echo "📋 実行コマンド: python src/main.py --manual --config config.ini"
echo

python src/main.py --manual --config config.ini

if [ $? -ne 0 ]; then
    echo
    echo "❌ トークン更新に失敗しました"
    echo "🔧 トラブルシューティング:"
    echo "  1. インターネット接続を確認"
    echo "  2. Googleアカウントの認証を確認"
    echo "  3. config.ini の設定を確認"
    echo
    exit 1
fi

echo
echo "✅ トークン更新が完了しました"
echo

# 新しいトークンファイルの確認
if [ ! -f "token.json" ]; then
    echo "❌ 新しいトークンファイルが生成されませんでした"
    exit 1
fi

echo "📄 新しいトークンファイルを確認しました"
echo "📊 ファイルサイズ: $(stat -c%s token.json) bytes"
echo

# トークン内容の表示（機密情報は除外）
echo "🔍 トークン情報（デバッグ用）:"
python -c "
import json
try:
    with open('token.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'  有効期限: {data.get(\"expiry\", \"不明\")}')
    print(f'  スコープ: {len(data.get(\"scopes\", []))} 個')
    print(f'  リフレッシュトークン: {\"あり\" if data.get(\"refresh_token\") else \"なし\"}')
except Exception as e:
    print(f'  エラー: {e}')
"
echo

# GitHub Secrets更新のガイダンス
echo "========================================"
echo " GitHub Secrets 更新手順"
echo "========================================"
echo
echo "📋 以下の手順でGitHub Secretsを更新してください:"
echo
echo "1️⃣ GitHubリポジトリページにアクセス"
echo "   https://github.com/megane2501h/Aikatsu-academy_Schedule"
echo
echo "2️⃣ Settings > Secrets and variables > Actions"
echo
echo "3️⃣ GOOGLE_TOKEN を選択して「Update」をクリック"
echo
echo "4️⃣ 以下の内容をコピーして貼り付け:"
echo

# トークンファイルの内容を表示
echo "📋 新しいトークン内容（これをコピーしてください）:"
echo "----------------------------------------"
cat token.json
echo "----------------------------------------"
echo

# 自動コピー機能（macOS/Linux）
echo "🤖 自動コピー機能を試行中..."
if command -v pbcopy >/dev/null 2>&1; then
    # macOS
    cat token.json | pbcopy
    echo "✅ トークン内容をクリップボードにコピーしました（macOS）"
elif command -v xclip >/dev/null 2>&1; then
    # Linux (xclip)
    cat token.json | xclip -selection clipboard
    echo "✅ トークン内容をクリップボードにコピーしました（Linux）"
elif command -v xsel >/dev/null 2>&1; then
    # Linux (xsel)
    cat token.json | xsel --clipboard --input
    echo "✅ トークン内容をクリップボードにコピーしました（Linux）"
else
    echo "⚠️  自動コピー機能が利用できません"
    echo "📋 上記の内容を手動でコピーしてください"
fi
echo

# 完了メッセージ
echo "========================================"
echo " ✅ トークン更新完了"
echo "========================================"
echo
echo "🎯 次のステップ:"
echo "  1. 上記のトークン内容をGitHub Secretsに設定"
echo "  2. GitHub Actionsで同期テストを実行"
echo "  3. 問題が解決したことを確認"
echo
echo "💡 ヒント:"
echo "  - サービスアカウント認証への移行も検討してください"
echo "  - docs/SERVICE_ACCOUNT_SETUP.md を参照"
echo

# 対話的な確認
read -p "Enterキーを押して終了してください..." 