@echo off
rem Redirect active RDP session to console
for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (
  %windir%\System32\tscon.exe %%s /dest:console
)
timeout /t 5
qres /x 1440 /y 900 /c 32