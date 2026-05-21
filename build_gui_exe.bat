@echo off
REM Build script for PaperVaultQR GUI using PyInstaller

echo [1/4] Upgrading pip and checking dependencies...
python -m pip install --upgrade pip
pip install pyinstaller pyzbar Pillow segno python-docx customtkinter

echo.
set "SCRIPT_DIR=%~dp0"
set "BUILD_DIR=%SCRIPT_DIR%build\pyinstaller"
set "VERSION_FILE=%BUILD_DIR%\version.txt"
set "VERSION_SUFFIX="
if not "%PAPERVAULTQR_VERSION%"=="" set "VERSION_SUFFIX=-%PAPERVAULTQR_VERSION%"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
set "BUNDLE_VERSION=%PAPERVAULTQR_VERSION%"
if "%BUNDLE_VERSION%"=="" set "BUNDLE_VERSION=dev"
> "%VERSION_FILE%" echo %BUNDLE_VERSION%

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
REM 核心修复：将输出直接放到 release，避免 dist/release 双目录并存
if not exist release mkdir release
pyinstaller --onefile --windowed --clean ^
  --name PaperVaultQR-GUI%VERSION_SUFFIX% ^
  --distpath release ^
  --workpath "%BUILD_DIR%" ^
  --specpath "%BUILD_DIR%" ^
  --add-binary "%PYZBAR_PATH%\*.dll;pyzbar" ^
  --add-data "%CTK_PATH%;customtkinter" ^
  --add-data "%SCRIPT_DIR%src\i18n\locales;i18n\locales" ^
  --add-data "%VERSION_FILE%;." ^
  --add-data "%SCRIPT_DIR%src\icon;icon" ^
  src\gui.py

echo.
echo [4/4] Finalizing build...
if exist release\PaperVaultQR-GUI%VERSION_SUFFIX%.exe (
  echo ========================================================
  echo  SUCCESS! Built: release\PaperVaultQR-GUI%VERSION_SUFFIX%.exe
  echo ========================================================
) else (
  echo ERROR: Build failed. Check the logs above.
)
