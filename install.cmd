@echo off
setlocal
rem Bootstrap wrapper for install.py: resolves an interpreter
rem (uv -> python3 -> python) and delegates, forwarding all arguments.
rem Never hardcodes a bare python3/python without a PATH check first — see
rem anthropics/claude-code#16131 for the Windows trap this avoids (bare
rem `python` can be a Windows Store stub).
set "dir=%~dp0"
set "target=%dir%install.py"

where uv >nul 2>nul
if not errorlevel 1 (
    uv run --no-project python "%target%" %*
    exit /b %errorlevel%
)

where python3 >nul 2>nul
if not errorlevel 1 (
    python3 "%target%" %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%target%" %*
    exit /b %errorlevel%
)

echo error: no python interpreter found (tried uv, python3, python) 1>&2
exit /b 1
