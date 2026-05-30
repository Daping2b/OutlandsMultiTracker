# -*- mode: python ; coding: utf-8 -*-
# OutlandsMultiTracker PyInstaller spec
# console=False temporarily to see image debug output
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets',  'assets'),
        ('config',  'config'),
        ('scripts', 'scripts'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',
        'matplotlib.backends.backend_tkagg',
        'pystray._win32',
        'numpy',
        'tkcalendar',
        'babel.numbers',
        'babel.dates',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OutlandsMultiTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # <-- set True to see debug output, change to False once images work
    icon='assets\\O-MTSmall.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OutlandsMultiTracker',
)
