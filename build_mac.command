#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV=".desktop_build_venv"

echo "HT-SmartScheduler macOS packager"
echo "================================"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 is required to BUILD the app. End users will not need Python."
  exit 1
fi

if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi
source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt "pyinstaller>=6.0,<7.0"

ADD_DATA=()
if [ -d "nlp/model" ]; then
  ADD_DATA+=(--add-data "nlp/model:nlp/model")
fi
if [ -f "data/google_credentials.json" ]; then
  ADD_DATA+=(--add-data "data/google_credentials.json:data")
fi

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "HT-SmartScheduler" \
  --collect-all spacy \
  --collect-submodules googleapiclient \
  --collect-submodules google_auth_oauthlib \
  --collect-submodules google.auth \
  --collect-submodules google.oauth2 \
  "${ADD_DATA[@]}" \
  desktop_entry.py

echo
echo "BUILD COMPLETE"
echo "Open: dist/HT-SmartScheduler.app"
echo "End users do not need Python or pip."
