@echo off
chcp 65001 >nul
rem 게임 음성 번역기 — 디버그 실행 (콘솔에 로그가 보임)
cd /d "%~dp0"
".venv\Scripts\python.exe" gui.py
echo.
echo (프로그램이 종료되었습니다. 아무 키나 누르면 창이 닫힙니다.)
pause >nul
