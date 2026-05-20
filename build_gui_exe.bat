@echo off
REM Build script for PaperVaultQR GUI using PyInstaller

echo [1/4] Upgrading pip and checking dependencies...
python -m pip install --upgrade pip
pip install pyinstaller pyzbar Pillow segno python-docx customtkinter

echo.
echo [2/4] Locating DLL and UI dependencies...
FOR /F "tokens=*" %%g IN ('python -c "import os, pyzbar; print(os.path.dirname(pyzbar.__file__))"') do (SET PYZBAR_PATH=%%g)
FOR /F "tokens=*" %%g IN ('python -c "import os, customtkinter; print(os.path.dirname(customtkinter.__file__))"') do (SET CTK_PATH=%%g)

if "%PYZBAR_PATH%"=="" (
    echo ERROR: Could not find pyzbar library path!
    pause
    exit /b 1
)

echo Found pyzbar at: %PYZBAR_PATH%
echo Found customtkinter at: %CTK_PATH%

echo.
echo [3/4] Building PaperVaultQR GUI...
REM 核心修复：带上 pyzbar 的 DLL 以及 customtkinter 的主题 JSON 和图标资源！
pyinstaller --onefile --windowed --clean ^
  --add-binary "%PYZBAR_PATH%\*.dll;pyzbar" ^
  --add-data "%CTK_PATH%;customtkinter" ^
  gui.py

echo.
echo [4/4] Finalizing build...
if exist dist\gui.exe (
  if not exist release mkdir release
  copy /Y dist\gui.exe release\PaperVaultQR-GUI.exe >nul
  echo ========================================================
  echo  SUCCESS! Built: release\PaperVaultQR-GUI.exe
  echo ========================================================
) else (
  echo ERROR: Build failed. Check the logs above.
)
