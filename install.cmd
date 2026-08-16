@echo off
setlocal
rem Bootstrap wrapper for install.py: resolves an interpreter
rem (uv -> python3 -> python) and delegates, forwarding all arguments.
rem uv is tried first because a bare python3/python can be the Windows Store
rem stub, which `where` finds and cannot tell apart from an interpreter
rem -- see anthropics/claude-code#16131 for the trap the order avoids.
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
