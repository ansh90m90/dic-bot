@echo off
REM Runs the bot in a restart loop and logs everything to bot.log.
REM Launch via start-hidden.vbs (no window) or double-click for a visible window.
cd /d "%~dp0"

:loop
if exist "stop.flag" (
    del "stop.flag" >nul 2>&1
    echo [%date% %time%] stop flag found - exiting.>> bot.log
    exit /b 0
)
REM Keep the log from growing without bound (rotate at ~5 MB).
if exist bot.log (
    for %%F in (bot.log) do if %%~zF gtr 5242880 move /y bot.log bot.old.log >nul 2>&1
)
echo [%date% %time%] starting bot>> bot.log
python main.py >> bot.log 2>&1
echo [%date% %time%] bot stopped - restarting in 10s>> bot.log
ping -n 11 127.0.0.1 >nul
goto loop
