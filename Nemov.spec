# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources'), ('resources/icons/nemov.ico', '.')] + collect_data_files('imageio_ffmpeg') + collect_data_files('reportlab'),
    hiddenimports=[
        'nemov',
        'yalda',
        'arabic_reshaper',
        'bidi',
        'bidi.algorithm',
        'jdatetime',
        'sqlalchemy.dialects.sqlite',
        'PIL',
        'cv2',
        'imageio_ffmpeg',
        'openpyxl',
        'requests'
    ] + collect_submodules('reportlab') + collect_submodules('nemov') + collect_submodules('yalda'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Nemov',
    icon='resources/icons/nemov.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
a.binaries = [b for b in a.binaries if not any(x in b[0].lower() for x in ['opengl32sw', 'd3dcompiler'])]

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Nemov',
)
