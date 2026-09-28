@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_NAME=HT-SmartScheduler"
set "VERSION=11.6.3"
set "VENV=.desktop_build_venv"
set "PYTHON_CMD="

python -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  echo.
  echo Python 3 was not found.
  echo HT-SmartScheduler only needs Python on the computer used to BUILD the app.
  echo End users do not need Python.
  echo.
  echo If `py --version` works on this computer, please report this message.
  echo Otherwise install Python 3 for your user account, if allowed by your IT policy.
  exit /b 1
)

echo Using Python: %PYTHON_CMD%

if not exist "%VENV%\Scripts\python.exe" (
  echo Creating build environment...
  %PYTHON_CMD% -m venv "%VENV%"
  if errorlevel 1 (
    echo Failed to create the build environment.
    exit /b 1
  )
)

set "VENV_PY=%CD%\%VENV%\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo Build-environment Python was not created correctly.
  exit /b 1
)

set PIP_DISABLE_PIP_VERSION_CHECK=1
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

"%VENV_PY%" -m pip install -r requirements.txt "pyinstaller>=6.0,<7.0"
if errorlevel 1 exit /b 1

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release rmdir /s /q release
mkdir release

set "EXTRADATA="
if exist "nlp\model" set EXTRADATA=--add-data "nlp\model;nlp\model"
if exist "data\google_credentials.json" set EXTRADATA=%EXTRADATA% --add-data "data\google_credentials.json;data"

"%VENV_PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onefile ^
  --name "%APP_NAME%-Reminder" ^
  reminder_worker_entry.py
if errorlevel 1 exit /b 1

"%VENV_PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onefile ^
  --name "%APP_NAME%" ^
  --collect-all spacy ^
  --collect-submodules googleapiclient ^
  --collect-submodules google_auth_oauthlib ^
  --collect-submodules google.auth ^
  --collect-submodules google.oauth2 ^
  %EXTRADATA% ^
  desktop_entry.py
if errorlevel 1 exit /b 1

copy /y "dist\%APP_NAME%.exe" "release\%APP_NAME%.exe" >nul
copy /y "dist\%APP_NAME%-Reminder.exe" "release\%APP_NAME%-Reminder.exe" >nul

echo.
echo ========================================
echo BUILD COMPLETE
echo ========================================
echo Windows executable created:
echo   release\%APP_NAME%.exe
echo   release\%APP_NAME%-Reminder.exe
echo.
echo Keep both EXE files together. Double-click only HT-SmartScheduler.exe.
echo End users do not need Python or pip.
echo.
endlocal
