@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Vaelin UI 演示壳 · Desktop-S1 · DEMO · 非生产
echo  假数据 · 仅 127.0.0.1 · 零 Hermes · 禁公网隧道 · demo 不等于 production
echo  本窗口不是生产 Vaelin，也不是已接 Hermes 的安装包。
echo.
where node >nul 2>&1
if errorlevel 1 (
  echo [失败] 未找到 node。需要本机 Node.js。未改 Hermes。
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [失败] 未找到 npm。未改 Hermes。
  pause
  exit /b 1
)
if not exist "node_modules\electron\cli.js" (
  echo 首次运行：安装已钉死的 Electron 44.9.0（仅本地依赖，无自动更新、无商店签名）...
  call npm install --no-audit --no-fund --save-exact
  if errorlevel 1 (
    echo [失败] npm install 未成功。可删 demos\desktop\node_modules 后重试。未改 Hermes。
    pause
    exit /b 1
  )
)
call npm start
if errorlevel 1 (
  echo.
  echo [失败] 桌面窗未正常退出。见上方错误。未改 Hermes。
  pause
  exit /b 1
)
exit /b 0
