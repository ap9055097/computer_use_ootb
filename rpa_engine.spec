# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for RPA Engine Windows executable.

Build commands:
    # WITH console (for debugging, see URLs in terminal):
    pyinstaller rpa_engine.spec

    # WITHOUT console (production, windowed mode):
    # Change console=True to console=False below

Usage:
    pip install pyinstaller
    pip install -r requirements-api.txt
    pyinstaller rpa_engine.spec

Output will be in dist/RPA-Engine.exe
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all Gradio data files (templates, static assets, etc.)
gradio_datas = collect_data_files('gradio')
gradio_client_datas = collect_data_files('gradio_client')
safehttpx_datas = collect_data_files('safehttpx')
huggingface_hub_datas = collect_data_files('huggingface_hub')
groovy_datas = collect_data_files('groovy')
httplib2_datas = collect_data_files('httplib2')
markdown_it_datas = collect_data_files('markdown_it')

# Hidden imports required for Gradio and dependencies
hiddenimports = [
    # Gradio and web framework
    'gradio',
    'gradio.routes',
    'gradio.themes',
    'gradio.blocks',
    'gradio.components',
    'gradio_client',

    # Web server
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',

    # ASGI/HTTP
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'httpx',
    'httpcore',
    'anyio',
    'sniffio',

    # API clients
    'anthropic',
    'anthropic.types',
    'anthropic.types.beta',
    'google.generativeai',
    'boto3',
    'botocore',

    # GUI automation (Windows-specific)
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._win32',
    'pynput.mouse',
    'pynput.mouse._win32',
    'pyautogui',
    'uiautomation',

    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ImageGrab',
    'imagehash',

    # Utilities
    'screeninfo',
    'jsonschema',
    'pydantic',
    'numpy',

    # Windows notifications (optional)
    'win10toast',

    # Required by gradio_client for share functionality
    'huggingface_hub',
    'huggingface_hub.utils',
    'huggingface_hub.hf_api',

    # App module
    'app',
    'computer_use_demo',
    'computer_use_demo.loop',
    'computer_use_demo.tools',
    'computer_use_demo.tools.computer',
    'computer_use_demo.tools.logger',
]

# Collect submodules for packages that have many dynamic imports
hiddenimports += collect_submodules('gradio')
hiddenimports += collect_submodules('anthropic')
hiddenimports += collect_submodules('computer_use_demo')

a = Analysis(
    ['app_packaged.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Application data
        ('assets', 'assets'),
        ('computer_use_demo', 'computer_use_demo'),
        ('app.py', '.'),

        # Gradio data files
        *gradio_datas,
        *gradio_client_datas,
        *safehttpx_datas,
        *huggingface_hub_datas,
        *groovy_datas,
        *httplib2_datas,
        *markdown_it_datas,
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude ML libraries (not needed for API-only mode)
        'torch',
        'torchvision',
        'transformers',
        'accelerate',
        # 'huggingface_hub',  # NEEDED for gradio_client share functionality
        'qwen_vl_utils',
        'dashscope',

        # Exclude dev tools
        'pytest',
        'ruff',
        'pre_commit',

        # Exclude unused
        'tkinter',
        'matplotlib',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RPA-Engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for windowed mode (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='build/icon.ico',  # Uncomment when icon is available
)
