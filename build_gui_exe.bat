@echo off
REM Build script for PaperVaultQR GUI using PyInstaller
python -m pip install --upgrade pip
pip install pyinstaller
pyinstaller --onefile --windowed gui.py
if exist dist\gui.exe (
  if not exist release mkdir release
  copy dist\gui.exe release\PaperVaultQR-GUI.exe
  echo Built: release\PaperVaultQR-GUI.exe
) else (
  echo Build failed
)
pause
