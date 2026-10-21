@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Vaelin UI Demo Desktop-S2 DOM selftest - DEMO non-production
echo  probes: title / non-prod banner / screen ids / port 8766
echo.
where node >nul 2>&1
if errorlevel 1 (
  echo [FAIL] node not found. Hermes untouched.
  exit /b 1
)
if not exist "node_modules\electron\cli.js" (
  echo electron missing, npm install...
  call npm install --no-audit --no-fund --save-exact
  if errorlevel 1 (
    echo [FAIL] npm install failed. Hermes untouched.
    exit /b 1
  )
)
set "OUT=%CD%\selftest-out.json"
if exist "%OUT%" del /f /q "%OUT%" >nul 2>&1
set DESKTOP_S2_SELFTEST=1
set DESKTOP_S2_SELFTEST_OUT=%OUT%
set DESKTOP_S1_SELFTEST=
set DESKTOP_S1_SELFTEST_OUT=
echo running selftest...
call npm start
set EXITCODE=%ERRORLEVEL%
set DESKTOP_S2_SELFTEST=
set DESKTOP_S2_SELFTEST_OUT=
if not exist "%OUT%" (
  echo [FAIL] no selftest-out.json. exit=%EXITCODE%
  exit /b 1
)
node selftest_check.js "%OUT%"
set CHECK=%ERRORLEVEL%
if not "%CHECK%"=="0" (
  echo [FAIL] selftest_check failed.
  exit /b %CHECK%
)
if not "%EXITCODE%"=="0" (
  echo [FAIL] electron exit=%EXITCODE%
  exit /b %EXITCODE%
)
echo [PASS] Desktop-S2 DOM selftest
exit /b 0
