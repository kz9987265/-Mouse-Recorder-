@echo off
cd /d "%~dp0"

:: 檢查是否有管理員權限，沒有就自動跳出 UAC 提權
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 取得權限後，以背景無視窗方式啟動 pythonw 並關閉 CMD
start pythonw mouse_gui.pyw
exit