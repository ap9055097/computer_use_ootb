@echo off

REM 1. Switch to the correct drive & folder
cd /D "C:\Users\Administrator\computer_use_ootb"

REM 2. Activate the virtual environment
call .venv\Scripts\activate.bat

REM 3. Start the Gradio app with public share link
REM Note: Using python directly (not uvicorn) to get the public share link
python app.py