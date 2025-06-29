# Windows用セットアップスクリプト
# アイカツアカデミー！スケジュール同期ツール

Write-Host "=== アイカツアカデミー！スケジュール同期ツール セットアップ ===" -ForegroundColor Green

# uvのインストール確認
Write-Host "uvのインストール状況を確認中..." -ForegroundColor Yellow
$uvInstalled = $false
try {
    $uvVersion = uv --version
    Write-Host "uv is already installed: $uvVersion" -ForegroundColor Green
    $uvInstalled = $true
} catch {
    Write-Host "uvがインストールされていません。インストールを開始します..." -ForegroundColor Yellow
}

# uvのインストール
if (-not $uvInstalled) {
    try {
        pip install uv
        Write-Host "uvのインストールが完了しました。" -ForegroundColor Green
    } catch {
        Write-Host "uvのインストールに失敗しました。手動でインストールしてください。" -ForegroundColor Red
        Write-Host "コマンド: pip install uv" -ForegroundColor Yellow
        exit 1
    }
}

# 仮想環境の作成
Write-Host "仮想環境を作成中..." -ForegroundColor Yellow
try {
    uv venv
    Write-Host "仮想環境の作成が完了しました。" -ForegroundColor Green
} catch {
    Write-Host "仮想環境の作成に失敗しました。" -ForegroundColor Red
    exit 1
}

# 依存関係のインストール
Write-Host "依存関係をインストール中..." -ForegroundColor Yellow
try {
    uv sync
    Write-Host "依存関係のインストールが完了しました。" -ForegroundColor Green
} catch {
    Write-Host "依存関係のインストールに失敗しました。" -ForegroundColor Red
    exit 1
}

# 設定ファイルの作成
Write-Host "設定ファイルを作成中..." -ForegroundColor Yellow
if (-not (Test-Path "config.ini")) {
    try {
        .\.venv\Scripts\Activate.ps1
        cd src
        python main.py --create-config
        cd ..
        Write-Host "設定ファイル 'config.ini' を作成しました。" -ForegroundColor Green
    } catch {
        Write-Host "設定ファイルの作成に失敗しました。" -ForegroundColor Red
    }
} else {
    Write-Host "設定ファイル 'config.ini' は既に存在します。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== セットアップ完了 ===" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. Google Cloud Consoleでプロジェクトを作成し、Calendar APIを有効化"
Write-Host "2. credentials.jsonをプロジェクトルートに配置"
Write-Host "3. config.iniファイルを編集してCALENDAR_IDを設定"
Write-Host "4. 仮想環境をアクティベート: .\.venv\Scripts\Activate.ps1"
Write-Host "5. テスト実行: cd src && python main.py --manual"
Write-Host ""
Write-Host "詳細な手順については README.md を参照してください。" -ForegroundColor Cyan 