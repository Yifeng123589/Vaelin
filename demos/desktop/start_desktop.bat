@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Vaelin UI Demo Desktop-S2 - DEMO non-production
echo  fixture data - 127.0.0.1 only - zero Hermes - no public tunnel
echo  demo != production - install != enable - not a Hermes-connected installer
echo.
echo  [path] %CD%
echo  [port] default 8766@127.0.0.1 (fallback if busy; desktop default must NOT be 8765)
echo  [hint] closing the window stops the static server. optional tray: set DESKTOP_S2_TRAY=1
echo  [selftest] use run_selftest.bat for acceptance probes
echo.
where node >nul 2>&1
if errorlevel 1 (
  echo [FAIL] node not found. Install Node.js and add to PATH.
  echo        Hermes untouched. Did not write %%LocalAppData%%\hermes.
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [FAIL] npm not found. Complete Node.js install.
  echo        Hermes untouched.
  pause
  exit /b 1
)
if not exist "package.json" (
  echo [FAIL] package.json missing. Run this script inside demos\desktop.
  echo        cwd: %CD%
  pause
  exit /b 1
)
if not exist "main.js" (
  echo [FAIL] main.js missing. wrong path: %CD%
  pause
  exit /b 1
)
if not exist "node_modules\electron\cli.js" (
  echo first run: install pinned Electron 44.9.0 (local only, no autoupdate/codesign)...
  call npm install --no-audit --no-fund --save-exact
  if errorlevel 1 (
    echo [FAIL] npm install failed. You may delete demos\desktop\node_modules and retry. Hermes untouched.
    pause
    exit /b 1
  )
)
echo starting Electron demo window (non-production)...
call npm start
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo [FAIL] desktop window exited with code %EXITCODE%. See errors above. Hermes untouched.
  echo        If port busy: close old demo window and retry.
  pause
  exit /b %EXITCODE%
)
exit /b 0
