@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Vaelin UI Demo Desktop - DEMO non-production
echo  Hermes sandbox demo face (H-SBX-A stub) - NOT production LocalAppData\hermes
echo  sign != enable - demo != production - install != enable
echo  8766 != production Hermes - PUB != production enable
echo.
set "HERMES_HOME=%~dp0_hermes_sandbox_stub"
for %%I in ("%HERMES_HOME%") do set "HERMES_HOME=%%~fI"
echo  [path] %CD%
echo  [HERMES_HOME] %HERMES_HOME%
echo  [port] default 8766@127.0.0.1 (fallback if busy; desktop default must NOT be 8765)
echo  [hint] closing the window stops the static server. optional tray: set DESKTOP_S2_TRAY=1
echo  [help] F1 or ? for desktop keymap help; Ctrl+Shift+A for hard-gate About
echo  [selftest] use run_selftest.bat for acceptance probes
echo.
echo %HERMES_HOME% | findstr /I /C:"\AppData\Local\hermes" >nul
if not errorlevel 1 (
  echo [FAIL] HERMES_HOME looks like production LocalAppData\hermes. Refuse.
  pause
  exit /b 2
)
if not exist "%HERMES_HOME%\SANDBOX_MARKER.json" (
  echo [FAIL] sandbox stub marker missing: %HERMES_HOME%\SANDBOX_MARKER.json
  echo        Expected demos\desktop\_hermes_sandbox_stub\SANDBOX_MARKER.json
  echo        Production hermes untouched.
  pause
  exit /b 2
)
where node >nul 2>&1
if errorlevel 1 (
  echo [FAIL] node not found. Install Node.js and add to PATH.
  echo        Hermes production untouched. Did not write %%LocalAppData%%\hermes.
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [FAIL] npm not found. Complete Node.js install.
  echo        Hermes production untouched.
  pause
  exit /b 1
)
if not exist "package.json" (
  echo [FAIL] package.json missing. Run inside demos\desktop.
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
    echo [FAIL] npm install failed. Production hermes untouched.
    pause
    exit /b 1
  )
)
echo starting Electron demo window (Desktop Hermes-sandbox demo / non-production)...
call npm start
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo [FAIL] desktop window exited with code %EXITCODE%. Production hermes untouched.
  echo        If port busy: close old demo window and retry.
  pause
  exit /b %EXITCODE%
)
exit /b 0
