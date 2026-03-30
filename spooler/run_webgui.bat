@echo off
setlocal

cd /d "%~dp0"

if not "%AGENT_VENV%"=="" (
    set "VENV_PATH=%AGENT_VENV%"
    echo [SETUP] Using override venv at %VENV_PATH%
) else (
    set "VENV_PATH=%~dp0venv"
    echo [SETUP] Using server venv at %VENV_PATH%
)

if not exist "%VENV_PATH%" (
    echo [SETUP] Creating virtual environment...
    python -m venv "%VENV_PATH%"
)

echo [SETUP] Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

echo [SETUP] Installing dependencies...
pip install --upgrade pip
pip install -r "%~dp0requirements.txt"

REM Forwarder target settings (daemon stream endpoint)
REM Usage:
REM   run_webgui.bat                  -> default ws://127.0.0.1:8765
REM   run_webgui.bat 192.168.1.102    -> ws://192.168.1.102:8765
REM   run_webgui.bat 192.168.1.102 9000 -> ws://192.168.1.102:9000
if not "%~1"=="" (
    if "%~2"=="" (
        set "SPOOLER_FORWARDER_URL=ws://%~1:8765"
    ) else (
        set "SPOOLER_FORWARDER_URL=ws://%~1:%~2"
    )
)
if "%SPOOLER_FORWARDER_URL%"=="" set "SPOOLER_FORWARDER_URL=ws://127.0.0.1:8765"
echo [NET] Forwarder target: %SPOOLER_FORWARDER_URL%
if "%SPOOLER_FORWARDER_URL%"=="ws://127.0.0.1:8765" echo [NET] Mode: local daemon (same machine)

echo [RUN] Starting Spooler Web GUI on http://0.0.0.0:8949
python "%~dp0webgui.py"

endlocal
