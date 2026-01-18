@echo off
setlocal

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "VENV_PYTHON=%ROOT_DIR%\venv\Scripts\python.exe"
set "PYTHON_SCRIPT=%ROOT_DIR%\src\Working_Code.py"

:: Check if VENV python exists
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at %ROOT_DIR%\venv
    echo Please run Install.ps1 first.
    exit /b 1
)

:: Run the script with all arguments passed
"%VENV_PYTHON%" "%PYTHON_SCRIPT%" %*

endlocal
