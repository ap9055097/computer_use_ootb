"""
Build script for creating Windows executable using PyInstaller.

This script automates the build process:
1. Installs required dependencies
2. Runs PyInstaller with the spec file
3. Creates the output in dist/

Usage:
    python build/build_exe.py [--windowed]

Options:
    --windowed    Build without console window (production mode)

Requirements:
    - Python 3.12+
    - pip
    - Must be run on Windows for Windows executable
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


def install_dependencies():
    """Install required dependencies for API-only mode."""
    project_root = get_project_root()
    requirements_file = project_root / "requirements-api.txt"

    print("Installing dependencies from requirements-api.txt...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "-r", str(requirements_file)
    ])

    print("Installing PyInstaller...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "pyinstaller"
    ])


def build_executable(windowed=False):
    """Build the executable using PyInstaller."""
    project_root = get_project_root()
    spec_file = project_root / "rpa_engine.spec"

    # Read and optionally modify spec file for windowed mode
    if windowed:
        print("Building in WINDOWED mode (no console)...")
        spec_content = spec_file.read_text()
        spec_content = spec_content.replace("console=True", "console=False")

        # Write temporary spec file
        temp_spec = project_root / "rpa_engine_windowed.spec"
        temp_spec.write_text(spec_content)
        spec_to_use = temp_spec
    else:
        print("Building in CONSOLE mode (for debugging)...")
        spec_to_use = spec_file

    # Change to project root directory
    os.chdir(project_root)

    # Run PyInstaller
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            str(spec_to_use)
        ])
    finally:
        # Clean up temporary spec file
        if windowed:
            temp_spec.unlink(missing_ok=True)


def clean_build():
    """Clean up build artifacts."""
    project_root = get_project_root()

    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path != project_root / "build":
            print(f"Cleaning {dir_path}...")
            shutil.rmtree(dir_path, ignore_errors=True)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Build RPA Engine Windows executable")
    parser.add_argument(
        "--windowed", "-w",
        action="store_true",
        help="Build without console window (production mode)"
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Clean build artifacts before building"
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip installing dependencies"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("RPA Engine Windows Build Script")
    print("=" * 60)

    if args.clean:
        clean_build()

    if not args.skip_deps:
        install_dependencies()

    build_executable(windowed=args.windowed)

    print()
    print("=" * 60)
    print("Build complete!")
    print(f"Output: {get_project_root() / 'dist' / 'RPA-Engine.exe'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
