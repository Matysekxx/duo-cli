@echo off
setlocal
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %*
) else if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" "%~dp0main.py" %*
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py "%~dp0main.py" %*
    ) else (
        python "%~dp0main.py" %*
    )
)
endlocal
