"""
Entry point for packaged .exe version.
Wraps the original app.py and handles URL display for windowed mode.

This file is used by PyInstaller to create the Windows executable.
The original app.py is imported and its demo is launched with custom settings.
"""
import sys
import os

# Set up paths for PyInstaller bundled app
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = sys._MEIPASS
    # Change working directory to where the exe is located
    os.chdir(os.path.dirname(sys.executable))
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add base dir to path so we can import app module
sys.path.insert(0, BASE_DIR)

# Import the demo from original app.py
from app import demo


def main():
    """Launch the Gradio demo with URL capture and display."""

    # Launch with URL capture
    app, local_url, share_url = demo.launch(
        share=True,
        share_server_address="rpavialink.com:7000",
        share_server_protocol="https",
        allowed_paths=["./"],
        server_port=7888,
        inbrowser=True,  # Auto-open browser
        prevent_thread_lock=True  # Don't block so we can handle URL
    )

    # Write URL to file for easy access
    try:
        with open("public_url.txt", "w", encoding="utf-8") as f:
            f.write(f"Local URL: {local_url}\n")
            f.write(f"Public URL: {share_url}\n")
        print(f"URLs saved to public_url.txt")
        print(f"Local: {local_url}")
        print(f"Public: {share_url}")
    except Exception as e:
        print(f"Warning: Could not write URL file: {e}")

    # Optional: Windows notification (toast)
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            "RPA Engine Started",
            f"Public URL: {share_url}",
            duration=10,
            threaded=True
        )
    except ImportError:
        # win10toast not installed, skip notification
        pass
    except Exception as e:
        # Notification failed, not critical
        print(f"Warning: Could not show notification: {e}")

    # Keep the server running
    demo.block()


if __name__ == "__main__":
    main()
