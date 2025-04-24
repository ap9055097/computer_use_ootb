# run_app.py
import uvicorn
from .app import demo  # assume this returns your gradio.Blocks()

if __name__ == "__main__":
    uvicorn.run(demo.app, host="127.0.0.1", port=7888)