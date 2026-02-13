@echo off

REM 1. Switch to the correct drive & folder
cd /D "C:\Users\Administrator\computer_use_ootb"

REM 2. Activate the virtual environment
call .venv\Scripts\activate.bat

REM 3. Start Uvicorn (you can also use python -m uvicorn…)
REM Note: app:demo because Gradio Blocks is an ASGI app, no need to call demo.launch()
uvicorn app:demo --host 127.0.0.1 --port 7888 --loop asyncio