@echo off
REM Change to your app directory
cd /d C:\Users\Administrator\computer_use_ootb

REM Activate the virtual environment (.env)
call .env\Scripts\activate.bat

REM Launch Uvicorn with your app module
python -m uvicorn app:app --host 127.0.0.1 --port 7888