@echo off
setlocal
echo Stopping OfficeSim server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F >nul 2>nul
)
echo Done.
pause
