@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Vaelin UI Demo Desktop DOM selftest - Hermes sandbox stub face
echo  probes: Desktop-S3 title / sign!=enable / 8766 / sandbox stub / not prod hermes
echo.
set "HERMES_HOME=%~dp0_hermes_sandbox_stub"
for %%I in ("%HERMES_HOME%") do set "HERMES_HOME=%%~fI"
echo  [HERMES_HOME] %HERMES_HOME%
echo %HERMES_HOME% | findstr /I /C:"\AppData\Local\hermes" >nul
if not errorlevel 1 (
  echo [FAIL] HERMES_HOME points at production. Refuse.
  exit /b 2
)
if not exist "%HERMES_HOME%\SANDBOX_MARKER.json" (
  echo [FAIL] sandbox stub marker missing.
  exit /b 2
)
where node >nul 2>&1
if errorlevel 1 (
  echo [FAIL] node not found. Production hermes untouched.
  exit /b 1
)
if not exist "node_modules\electron\cli.js" (
  echo electron missing, npm install...
  call npm install --no-audit --no-fund --save-exact
  if errorlevel 1 (
    echo [FAIL] npm install failed. Production hermes untouched.
    exit /b 1
  )
)
set "OUT=%CD%\selftest-out.json"
if exist "%OUT%" del /f /q "%OUT%" >nul 2>&1
set DESKTOP_S3_SELFTEST=1
set DESKTOP_S3_SELFTEST_OUT=%OUT%
set DESKTOP_S2_SELFTEST=
set DESKTOP_S2_SELFTEST_OUT=
set DESKTOP_S1_SELFTEST=
set DESKTOP_S1_SELFTEST_OUT=
echo running selftest...
call npm start
set EXITCODE=%ERRORLEVEL%
set DESKTOP_S3_SELFTEST=
set DESKTOP_S3_SELFTEST_OUT=
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
echo [PASS] Desktop Hermes-sandbox demo selftest
exit /b 0
