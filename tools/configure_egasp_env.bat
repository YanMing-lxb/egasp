@echo off
setlocal enabledelayedexpansion

cls
echo ========================================
echo   EGASP Environment Variable Configurator
echo ========================================
echo.
echo This script configures the EGASP environment variable
echo to make the egasp command available system-wide.
echo.

:: Check if EGASP files exist
echo [1/2] Checking EGASP files...
if not exist "egasp.exe" (
    echo [ERROR] EGASP executable not found. Please run this script in the correct directory.
    goto ErrorExit
)
echo [OK] EGASP files check passed

:: Add environment variable
echo [2/2] Configuring environment variable...
echo Adding EGASP to user PATH...

:: Get current directory
set "CURRENT_DIR=%~dp0"
set "EGASP_BIN=%CURRENT_DIR%"

:: Remove trailing backslash if exists
if "%EGASP_BIN:~-1%"=="\" set "EGASP_BIN=%EGASP_BIN:~0,-1%"

:: Check if path already exists
SET "PATH_EXISTS=0"
SET "MYPATHCOPY=%PATH%"
call :SearchPath

if %PATH_EXISTS% equ 1 (
    echo [INFO] EGASP is already in environment variable
) else (
    :: Add to current session temporarily
    set "PATH=%PATH%;%EGASP_BIN%"
    
    :: Add to user environment variable permanently
    powershell -Command "$oldPath = [Environment]::GetEnvironmentVariable('PATH', 'User'); if ($oldPath -notlike '*%EGASP_BIN%*') { [Environment]::SetEnvironmentVariable('PATH', \"$oldPath;%EGASP_BIN%\", 'User'); Write-Host '[OK] Environment variable added successfully' } else { Write-Host '[INFO] Path already exists, no need to add' }"
    
    if %errorlevel% equ 0 (
        echo [INFO] Please reopen command prompt for changes to take effect
    ) else (
        echo [WARNING] Failed to add environment variable automatically
        echo [INFO] Please manually run these PowerShell commands:
        echo [INFO]   $oldPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
        echo [INFO]   [Environment]::SetEnvironmentVariable('PATH', \"$oldPath;%EGASP_BIN%\", 'User')
    )
)

echo.
echo ========================================
echo   Installation completed!
echo ========================================
echo.
echo Available commands:
echo   - egasp: Run EGASP main program
echo   - To install Excel/WPS add-in:
echo     Double-click "%CURRENT_DIR%EGASP_Addin.xlam"
echo.
echo Note: If egasp command is not available, please reopen command prompt or add environment variable manually
pause
goto End

:SearchPath
for /f "tokens=1* delims=;" %%a in ("%MYPATHCOPY%") do (
    set "CURRENT_PATH=%%a"
    :: Remove trailing backslash if exists
    if "!CURRENT_PATH:~-1!"=="\" set "CURRENT_PATH=!CURRENT_PATH:~0,-1!"
    if /i "%EGASP_BIN%"=="!CURRENT_PATH!" (
        SET "PATH_EXISTS=1"
        goto :EOF
    )
    set "MYPATHCOPY=%%b"
    if not "!MYPATHCOPY!"=="" goto SearchPath
)
goto :EOF

:ErrorExit
echo ========================================
echo   Installation failed!
echo ========================================
echo Please check the error message above and try to resolve the issue.
echo.
pause

:End
