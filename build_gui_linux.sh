#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Upgrading pip and checking dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller pyzbar Pillow segno python-docx customtkinter

echo
echo "[2/4] Checking system library requirements..."
if ! python3 - <<'PY'
import ctypes.util
import sys

if ctypes.util.find_library("zbar") is None:
    sys.exit(1)
PY
then
  echo "WARNING: libzbar was not found."
  echo "         Install it with your package manager (for example: sudo apt-get install libzbar0)."
fi

echo
echo "[3/4] Building PaperVaultQR GUI..."
mkdir -p release build/pyinstaller

pyinstaller --onefile --windowed --clean \
  --name PaperVaultQR-GUI \
  --distpath release \
  --workpath build/pyinstaller \
  --specpath build/pyinstaller \
  --collect-all customtkinter \
  src/gui.py

echo
echo "[4/4] Finalizing build..."
if [ -f "release/PaperVaultQR-GUI" ]; then
  echo "========================================================"
  echo "SUCCESS! Built: release/PaperVaultQR-GUI"
  echo "========================================================"
else
  echo "ERROR: Build failed. Check the logs above."
  exit 1
fi
