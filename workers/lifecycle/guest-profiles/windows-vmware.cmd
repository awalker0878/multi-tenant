@echo off
rem This script runs only on the isolated destination copy.
start /wait "" "C:\ProgramData\Migration\setup64.exe" /S /v"/qn REBOOT=R"
if %ERRORLEVEL% EQU 3010 exit /b 0
if %ERRORLEVEL% NEQ 0 exit /b 249
rem libguestfs performs a reboot before continuing other firstboot scripts.
exit /b 0
