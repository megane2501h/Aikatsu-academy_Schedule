@echo off
chcp 65001 >nul

echo.
echo ========================================
echo  Google Calendar API �g�[�N���X�V�c�[��
echo ========================================
echo.

:: ���݂̃f�B���N�g�����m�F
echo ���݂̃f�B���N�g��: %CD%
echo.

:: �ݒ�t�@�C���̑��݊m�F
if not exist "config.ini" (
    echo ERROR: config.ini ��������܂���
    echo �v���W�F�N�g�̃��[�g�f�B���N�g���Ŏ��s���Ă�������
    pause
    exit /b 1
)

echo �ݒ�t�@�C�����m�F���܂���: config.ini
echo.

:: �����̃g�[�N���t�@�C���̊m�F
if exist "token.json" (
    echo �����̃g�[�N���t�@�C�����m�F���܂���
    for %%A in (token.json) do echo �t�@�C���T�C�Y: %%~zA bytes
    echo.
) else (
    echo �����̃g�[�N���t�@�C���͌�����܂���ł����i������s�j
    echo.
)

:: �g�[�N���X�V�̎��s
echo Google Calendar API �g�[�N�����X�V��...
echo ���s�R�}���h: python src/main.py --manual --config config.ini
echo.

python src/main.py --manual --config config.ini

if %ERRORLEVEL% neq 0 (
    echo.
    echo �g�[�N���X�V�Ɏ��s���܂���
    echo �g���u���V���[�e�B���O:
    echo   1. �C���^�[�l�b�g�ڑ����m�F
    echo   2. Google�A�J�E���g�̔F�؂��m�F
    echo   3. config.ini �̐ݒ���m�F
    echo.
    pause
    exit /b 1
)

echo.
echo �g�[�N���X�V���������܂���
echo.

:: �V�����g�[�N���t�@�C���̊m�F
if not exist "token.json" (
    echo �V�����g�[�N���t�@�C������������܂���ł���
    pause
    exit /b 1
)

echo �V�����g�[�N���t�@�C�����m�F���܂���
for %%A in (token.json) do echo �t�@�C���T�C�Y: %%~zA bytes
echo.

:: �g�[�N�����e�̕\���i�@�����͏��O�j
echo �g�[�N�����i�f�o�b�O�p�j:
python -c "import json; data=json.load(open('token.json')); print('�L������:', data.get('expiry', '�s��')); print('�X�R�[�v:', len(data.get('scopes', [])), '��'); print('���t���b�V���g�[�N��:', '����' if data.get('refresh_token') else '�Ȃ�')"
echo.

:: GitHub Secrets�X�V�̃K�C�_���X
echo ========================================
echo  GitHub Secrets �X�V�菇
echo ========================================
echo.
echo �ȉ��̎菇��GitHub Secrets���X�V���Ă�������:
echo.
echo 1. GitHub���|�W�g���y�[�W�ɃA�N�Z�X
echo    https://github.com/megane2501h/Aikatsu-academy_Schedule
echo.
echo 2. Settings > Secrets and variables > Actions
echo.
echo 3. GOOGLE_TOKEN ��I�����āuUpdate�v���N���b�N
echo.
echo 4. �ȉ��̓��e���R�s�[���ē\��t��:
echo.

:: �g�[�N���t�@�C���̓��e��\��
echo �V�����g�[�N�����e�i������R�s�[���Ă��������j:
echo ----------------------------------------
type token.json
echo ----------------------------------------
echo.

:: �����R�s�[�@�\�iWindows 10�ȍ~�j
echo �����R�s�[�@�\�����s��...
python -c "
import json
import subprocess
try:
    with open('token.json', 'r', encoding='utf-8') as f:
        token_content = f.read()
    subprocess.run(['clip'], input=token_content.encode('utf-8'), check=True)
    print('�g�[�N�����e���N���b�v�{�[�h�ɃR�s�[���܂���')
    print('����GitHub Secrets�ɓ\��t���Ă�������')
except Exception as e:
    print('�����R�s�[�Ɏ��s���܂���')
    print('��L�̓��e���蓮�ŃR�s�[���Ă�������')
"
echo.

:: �������b�Z�[�W
echo ========================================
echo  �g�[�N���X�V����
echo ========================================
echo.
echo ���̃X�e�b�v:
echo   1. ��L�̃g�[�N�����e��GitHub Secrets�ɐݒ�
echo   2. GitHub Actions�œ����e�X�g�����s
echo   3. ��肪�����������Ƃ��m�F
echo.
echo �q���g:
echo   - �T�[�r�X�A�J�E���g�F�؂ւ̈ڍs���������Ă�������
echo   - docs/SERVICE_ACCOUNT_SETUP.md ���Q��
echo.

pause 