@echo off

REM 1. Switch to the correct drive & folder
cd /D "C:\Users\Administrator\computer_use_ootb"

REM 2. Activate the virtual environment
call .venv\Scripts\activate.bat

REM 3. Start Uvicorn (you can also use python -m uvicorn…)
uvicorn app:app --host 127.0.0.1 --port 7888 --loop asyncio