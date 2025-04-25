@echo off
for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (
  %windir%\System32\tscon.exe %%s /dest:console
)
timeout /t 10
"C:\Tools\QRes.exe" /x:1440 /y:900 /c:32 /r:60