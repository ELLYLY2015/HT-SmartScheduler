@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_NAME=HT-SmartScheduler"
set "VENV=.desktop_build_venv"
set "PYTHON_CMD="

echo HT-SmartScheduler Windows packager
echo ================================

python -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  echo.
  echo Python 3 was not found. A developer Python install is required to BUILD the EXE.
  echo End users do not need Python.
  exit /b 1
)

echo Using Python: %PYTHON_CMD%

if not exist "%VENV%\Scripts\python.exe" (
  %PYTHON_CMD% -m venv "%VENV%"
  if errorlevel 1 goto :error
)

set "VENV_PY=%CD%\%VENV%\Scripts\python.exe"
set PIP_DISABLE_PIP_VERSION_CHECK=1
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirements.txt "pyinstaller>=6.0,<7.0"
if errorlevel 1 goto :error

set "EXTRADATA="
if exist "nlp\model" set EXTRADATA=--add-data "nlp\model;nlp\model"
if exist "data\google_credentials.json" set EXTRADATA=%EXTRADATA% --add-data "data\google_credentials.json;data"

"%VENV_PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "%APP_NAME%-Reminder" ^
  reminder_worker_entry.py
if errorlevel 1 goto :error

"%VENV_PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "%APP_NAME%" ^
  --collect-all spacy ^
  --collect-submodules googleapiclient ^
  --collect-submodules google_auth_oauthlib ^
  --collect-submodules google.auth ^
  --collect-submodules google.oauth2 ^
  %EXTRADATA% ^
  desktop_entry.py
if errorlevel 1 goto :error

echo.
echo BUILD COMPLETE
echo Open: dist\%APP_NAME%.exe
echo Background worker: dist\%APP_NAME%-Reminder.exe
echo Keep both EXE files together in the same folder.
echo End users do not need Python or pip.
exit /b 0

:error
echo.
echo Build failed. Review the error above.
exit /b 1
