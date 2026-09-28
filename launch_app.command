#!/bin/bash
cd "$(dirname "$0")"

if command -v python >/dev/null 2>&1; then
    exec python app.py
elif command -v python3 >/dev/null 2>&1; then
    exec python3 app.py
else
    echo "Python was not found."
    read -p "Press Enter to close."
fi
