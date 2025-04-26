@echo off
REM 1) Transfer RDP to console
for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (
  %windir%\System32\tscon.exe %%s /dest:console
)

REM 2) Wait briefly for session attach
timeout /t 5 /nobreak

REM 3) Enforce resolution via QRes
"C:\Tools\QRes.exe" /X:1440 /Y:900

REM 4) Fallback via PowerShell (if ServerCore module is available)
powershell -Command "Import-Module ServerCore; Set-DisplayResolution -Width 1440 -Height 900 -Force"