@echo off
REM OfficeSim Quick Launch Wrapper
REM This runs the launch.ps1 script with a bypassed execution policy.
powershell -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
