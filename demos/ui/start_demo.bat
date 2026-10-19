@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Vaelin UI 演示壳 S9 · 非生产 · 127.0.0.1 only · 零 Hermes
echo  打开: http://127.0.0.1:8765/
echo  快捷键: ? 帮助 · g 干净 · Shift+D 双栏 · c 清单 · r REC · Shift+C 字幕
echo  停止: Ctrl+C
echo.
start "" "http://127.0.0.1:8765/"
python -m http.server 8765 --bind 127.0.0.1
