@echo off
cd /d "%~dp0"
echo stop > "stop.flag"
schtasks /End /TN "FoolsAttendant" >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'main.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
echo The bot has been stopped.
pause
