@echo off
setlocal enabledelayedexpansion
title Far Far West - Gold Editor Launcher

:: ---------------------------------------------------------------------------
::  Far Far West Gold Editor - Smart Launcher
::  Checks Python, installs dependencies, launches the editor.
::  Double-click this file to run.
:: ---------------------------------------------------------------------------

cd /d "%~dp0"
set "REQUIRED_PKGS=pymem customtkinter psutil"

echo.
echo  ============================================
echo    Far Far West - Gold Editor
echo  ============================================
echo.

:: ── Step 1: Find Python ──────────────────────────────────────────────────

set "PYTHON="

:: Try python first (most common)
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('python --version 2^>^&1') do set "PYVER=%%i"
    echo  [OK] Found: !PYVER!
    set "PYTHON=python"
    goto :check_pkgs
)

:: Try python3
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('python3 --version 2^>^&1') do set "PYVER=%%i"
    echo  [OK] Found: !PYVER!
    set "PYTHON=python3"
    goto :check_pkgs
)

:: Try py launcher
where py >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('py --version 2^>^&1') do set "PYVER=%%i"
    echo  [OK] Found: !PYVER!
    set "PYTHON=py"
    goto :check_pkgs
)

:: Not found - offer to install
echo  [!!] Python is not installed on this computer.
echo.
echo  This tool needs Python to run. Install it now?
echo.
echo    [1] Yes - install Python automatically (recommended)
echo    [2] Yes - use winget (Windows package manager)
echo    [3] No  - open Python download page in browser
echo    [4] Cancel
echo.
set /p "CHOICE=  Choose (1-4): "

if "!CHOICE!"=="1" goto :install_python_wizard
if "!CHOICE!"=="2" goto :install_python_winget
if "!CHOICE!"=="3" goto :open_download_page
if "!CHOICE!"=="4" goto :cancel
goto :cancel

:: ── Install Python via direct download ───────────────────────────────────

:install_python_wizard
echo.
echo  Downloading Python 3.11 installer...
set "PYTHON_INSTALLER=%TEMP%\python-3.11-installer.exe"

:: Use PowerShell to download
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing" 2>nul

if not exist "%PYTHON_INSTALLER%" (
    echo  [!!] Download failed. Trying winget...
    goto :install_python_winget
)

echo  Running installer (this may take a minute)...
echo  Make sure to check "Add Python to PATH" in the installer!
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

del "%PYTHON_INSTALLER%" 2>nul

:: Refresh PATH
call :refresh_env

:: Check again
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON=python"
    echo  [OK] Python installed successfully!
    goto :check_pkgs
)

echo  [!!] Python install may need a restart to take effect.
echo  Please restart your computer and run this launcher again.
pause
exit /b 1

:: ── Install Python via winget ────────────────────────────────────────────

:install_python_winget
echo.
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!!] winget is not available on this system.
    goto :open_download_page
)

echo  Installing Python via winget...
winget install Python.Python.3.11 --silent --accept-package-agreements

if %errorlevel% neq 0 (
    echo  [!!] winget install failed.
    goto :open_download_page
)

call :refresh_env

where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON=python"
    echo  [OK] Python installed via winget!
    goto :check_pkgs
)

echo  [!!] Installation may need a restart. Please restart and try again.
pause
exit /b 1

:: ── Open download page ───────────────────────────────────────────────────

:open_download_page
echo.
echo  Opening Python download page in your browser...
echo  Download and install Python, then run this launcher again.
echo  IMPORTANT: Check "Add Python to PATH" during installation!
start https://www.python.org/downloads/
pause
exit /b 1

:: ── Cancel ───────────────────────────────────────────────────────────────

:cancel
echo.
echo  Python is required to run this tool.
echo  Install it manually from: https://www.python.org/downloads/
pause
exit /b 1

:: ── Step 2: Install required packages ────────────────────────────────────

:check_pkgs
echo.
echo  Checking required packages...

for %%p in (%REQUIRED_PKGS%) do (
    echo    Checking %%p...
    !PYTHON! -c "import %%p" 2>nul
    if !errorlevel! neq 0 (
        echo    Installing %%p...
        !PYTHON! -m pip install %%p --quiet --disable-pip-version-check 2>nul
        if !errorlevel! neq 0 (
            echo    [!] Failed to install %%p. Trying with --user...
            !PYTHON! -m pip install %%p --user --quiet --disable-pip-version-check 2>nul
        )
        !PYTHON! -c "import %%p" 2>nul
        if !errorlevel! neq 0 (
            echo.
            echo  [!!] Could not install %%p.
            echo  Please check your internet connection and try again.
            pause
            exit /b 1
        )
        echo    [OK] %%p installed
    ) else (
        echo    [OK] %%p already installed
    )
)

:: ── Step 3: Launch the editor ───────────────────────────────────────────

echo.
echo  ============================================
echo    Starting Gold Editor...
echo    If the game is not running, the editor
echo    will wait and auto-attach when detected.
echo  ============================================
echo.

:: Launch with pythonw to hide the console window
start "" !PYTHON!w "%~dp0editor.pyw" 2>nul
if %errorlevel% neq 0 (
    :: pythonw might not exist; fall back to python
    start "" !PYTHON! "%~dp0editor.pyw"
)

:: Brief pause so the user can read the output
timeout /t 2 /nobreak >nul
exit /b 0

:: ── Helper: refresh environment variables ────────────────────────────────

:refresh_env
:: Refresh PATH by re-reading from registry
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SysPath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "UserPath=%%b"
set "PATH=%SysPath%;%UserPath%;%PATH%"
goto :eof
