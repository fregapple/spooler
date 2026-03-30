@echo off
setlocal

REM Move to the directory this script lives in
cd /d "%~dp0"

REM Decide which venv to use
if not "%AGENT_VENV%"=="" (
    set "VENV_PATH=%AGENT_VENV%"
    echo [SETUP] Using override venv at %VENV_PATH%
) else (
    set "VENV_PATH=%~dp0venv"
    echo [SETUP] Using server venv at %VENV_PATH%
)

REM Create venv if missing
if not exist "%VENV_PATH%" (
    echo [SETUP] Creating virtual environment...
    python -m venv "%VENV_PATH%"
)

REM Activate venv
echo [SETUP] Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

REM Install dependencies
echo [SETUP] Installing dependencies...
pip install --upgrade pip
pip install -r "%~dp0requirements.txt"

REM Forwarder bind settings (for WebGUI connection)
REM Usage:
REM   run.bat                -> default 127.0.0.1:8765
REM   run.bat 0.0.0.0        -> bind all interfaces on port 8765
REM   run.bat 0.0.0.0 8765   -> bind all interfaces on specific port
if not "%~1"=="" set "SPOOLER_FORWARDER_HOST=%~1"
if not "%~2"=="" set "SPOOLER_FORWARDER_PORT=%~2"
if "%SPOOLER_FORWARDER_HOST%"=="" set "SPOOLER_FORWARDER_HOST=127.0.0.1"
if "%SPOOLER_FORWARDER_PORT%"=="" set "SPOOLER_FORWARDER_PORT=8765"
echo [NET] Forwarder bind: %SPOOLER_FORWARDER_HOST%:%SPOOLER_FORWARDER_PORT%
if "%SPOOLER_FORWARDER_HOST%"=="127.0.0.1" echo [NET] Mode: local daemon only (same machine)

REM Run daemon
cls
echo  _______  _______  _______  _______  ___      _______  ______
echo ^|       ^|^|       ^|^|       ^|^|       ^|^|   ^|    ^|       ^|^|    _ ^|
echo ^|  _____^|^|    _  ^|^|   _   ^|^|   _   ^|^|   ^|    ^|    ___^|^|   ^| ^|^|
echo ^| ^|_____ ^|   ^|_^| ^|^|  ^| ^|  ^|^|  ^| ^|  ^|^|   ^|    ^|   ^|___ ^|   ^|_^|^|_
echo ^|_____  ^|^|    ___^|^|  ^|_^|  ^|^|  ^|_^|  ^|^|   ^|___ ^|    ___^|^|    __  ^|
echo  _____^| ^|^|   ^|    ^|       ^|^|       ^|^|       ^|^|   ^|___ ^|   ^|  ^| ^|
echo ^|_______^|^|___^|    ^|_______^|^|_______^|^|_______^|^|_______^|^|___^|  ^|_^|
echo(
echo          Spoolman - Centauri Carbon - Orcaslicer Bridge
echo ================================================================
echo(

echo [RUN] Starting SDCP --- Spoolman daemon...
python "%~dp0daemon.py"

endlocal