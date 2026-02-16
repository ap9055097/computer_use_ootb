#!/usr/bin/env python3
"""
Test script to validate all imports work before building with PyInstaller.
Run this on macOS to catch missing dependencies early.

Usage:
    python test_imports.py
"""

import sys
import importlib
from typing import List, Tuple

# ANSI colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Packages to test - grouped by category
CROSS_PLATFORM_PACKAGES = [
    # Gradio and web framework
    ("gradio", None),
    ("gradio.routes", None),
    ("gradio.themes", None),
    ("gradio.blocks", None),
    ("gradio.components", None),
    ("gradio_client", None),

    # Web server
    ("uvicorn", None),
    ("uvicorn.logging", None),
    ("uvicorn.loops", None),
    ("uvicorn.loops.auto", None),
    ("uvicorn.protocols", None),
    ("uvicorn.protocols.http", None),
    ("uvicorn.protocols.http.auto", None),
    ("uvicorn.lifespan", None),
    ("uvicorn.lifespan.on", None),

    # ASGI/HTTP
    ("starlette", None),
    ("starlette.routing", None),
    ("starlette.middleware", None),
    ("httpx", None),
    ("httpcore", None),
    ("anyio", None),
    ("sniffio", None),

    # API clients
    ("anthropic", None),
    ("anthropic.types", None),
    ("anthropic.types.beta", None),
    ("google.generativeai", None),
    ("boto3", None),
    ("botocore", None),

    # Image processing
    ("PIL", None),
    ("PIL.Image", None),
    ("imagehash", None),

    # Utilities
    ("screeninfo", None),
    ("jsonschema", None),
    ("pydantic", None),
    ("numpy", None),

    # Gradio dependencies
    ("huggingface_hub", None),
    ("huggingface_hub.utils", None),
    ("huggingface_hub.hf_api", None),
    ("safehttpx", None),
    ("websockets", None),
    ("aiofiles", None),
    ("fsspec", None),
    ("tomlkit", None),
    ("typer", None),
    ("rich", None),
    ("shellingham", None),

    # pynput (cross-platform base)
    ("pynput", None),
    ("pynput.keyboard", None),
    ("pynput.mouse", None),

    # pyautogui (cross-platform)
    ("pyautogui", None),
]

# Windows-only packages - will be skipped on macOS
WINDOWS_ONLY_PACKAGES = [
    ("uiautomation", "Windows UI automation"),
    ("win10toast", "Windows notifications"),
    ("pynput.keyboard._win32", "Windows keyboard backend"),
    ("pynput.mouse._win32", "Windows mouse backend"),
    ("PIL.ImageGrab", "Screen capture (Windows/macOS only)"),
]

# Local app modules
APP_MODULES = [
    ("app", "Main Gradio app"),
    ("computer_use_demo", "Computer use demo package"),
    ("computer_use_demo.loop", "Main loop module"),
    ("computer_use_demo.tools", "Tools package"),
    ("computer_use_demo.tools.computer", "Computer tool"),
    ("computer_use_demo.tools.logger", "Logger tool"),
]


def test_import(module_name: str) -> Tuple[bool, str]:
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def test_package_group(packages: List[Tuple[str, str]], group_name: str, skip_on_failure: bool = False) -> Tuple[int, int]:
    """Test a group of packages and return (passed, failed) counts."""
    print(f"\n{'='*60}")
    print(f" {group_name}")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    for item in packages:
        if isinstance(item, tuple) and len(item) == 2:
            module_name, description = item
        else:
            module_name = item[0] if isinstance(item, tuple) else item
            description = None

        success, error = test_import(module_name)

        if success:
            print(f"{GREEN}✓{RESET} {module_name}")
            passed += 1
        else:
            if skip_on_failure:
                print(f"{YELLOW}⊘{RESET} {module_name} (skipped - {description or 'platform-specific'})")
            else:
                print(f"{RED}✗{RESET} {module_name}")
                print(f"  {RED}Error: {error}{RESET}")
                failed += 1

    return passed, failed


def main():
    print(f"\n{'#'*60}")
    print(f"# Import Test for RPA Engine")
    print(f"# Platform: {sys.platform}")
    print(f"# Python: {sys.version}")
    print(f"{'#'*60}")

    total_passed = 0
    total_failed = 0

    # Test cross-platform packages
    passed, failed = test_package_group(
        CROSS_PLATFORM_PACKAGES,
        "Cross-Platform Dependencies"
    )
    total_passed += passed
    total_failed += failed

    # Test Windows-only packages (skip on non-Windows)
    is_windows = sys.platform == "win32"
    passed, failed = test_package_group(
        WINDOWS_ONLY_PACKAGES,
        "Windows-Only Dependencies",
        skip_on_failure=not is_windows
    )
    if is_windows:
        total_passed += passed
        total_failed += failed

    # Test app modules
    passed, failed = test_package_group(
        APP_MODULES,
        "Application Modules"
    )
    total_passed += passed
    total_failed += failed

    # Summary
    print(f"\n{'='*60}")
    print(f" SUMMARY")
    print(f"{'='*60}")
    print(f"  {GREEN}Passed: {total_passed}{RESET}")
    print(f"  {RED}Failed: {total_failed}{RESET}")

    if total_failed > 0:
        print(f"\n{RED}Some imports failed! Fix these before building.{RESET}")
        print(f"Run: pip install -r requirements-api.txt")
        sys.exit(1)
    else:
        print(f"\n{GREEN}All imports successful! Ready to build.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
