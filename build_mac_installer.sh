#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="HT-SmartScheduler"
VERSION="11.6.3"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV=".desktop_build_venv"
RELEASE_DIR="release"
DIST_DIR="dist"
APP_PATH="$DIST_DIR/$APP_NAME.app"
DMG_NAME="HT-SmartScheduler-${VERSION}-macOS.dmg"
DMG_PATH="$RELEASE_DIR/$DMG_NAME"
STAGE_DIR=".dmg_stage"

printf '\nHT-SmartScheduler macOS installer builder\n'
printf '======================================\n\n'

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This installer must be built on macOS."
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 is required only to BUILD HT-SmartScheduler."
  echo "End users will not need Python."
  exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "hdiutil was not found. It is included with macOS."
  exit 1
fi

xattr -cr . 2>/dev/null || true

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

rm -rf build "$DIST_DIR" "$RELEASE_DIR" "$STAGE_DIR"
mkdir -p "$RELEASE_DIR"

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --collect-all spacy \
  --collect-submodules googleapiclient \
  --collect-submodules google_auth_oauthlib \
  --collect-submodules google.auth \
  --collect-submodules google.oauth2 \
  "${ADD_DATA[@]}" \
  desktop_entry.py

if [ ! -d "$APP_PATH" ]; then
  echo "Build failed: $APP_PATH was not created."
  exit 1
fi

xattr -cr "$APP_PATH" 2>/dev/null || true
if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$APP_PATH" >/dev/null 2>&1 || true
fi

mkdir -p "$STAGE_DIR"
cp -R "$APP_PATH" "$STAGE_DIR/"
ln -s /Applications "$STAGE_DIR/Applications"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH" >/dev/null

rm -rf "$STAGE_DIR"

printf '\nINSTALLER CREATED\n'
printf '=================\n'
printf '%s\n\n' "$DMG_PATH"
printf 'To install:\n'
printf '  1. Double-click %s\n' "$DMG_NAME"
printf '  2. Drag HT-SmartScheduler into Applications\n'
printf '  3. Open HT-SmartScheduler from Applications\n\n'
printf 'The installed app includes Python and required libraries.\n'
printf 'End users do not run pip, Python, or source code.\n\n'
printf 'For public distribution without Gatekeeper warnings, the app/DMG must be\n'
printf 'Developer ID signed and Apple-notarized.\n'
