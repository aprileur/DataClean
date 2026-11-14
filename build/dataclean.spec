# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.config import CONF
from PyInstaller.utils.hooks import collect_data_files

# Anclar resolución de rutas relativas a la raíz del repositorio
ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, '..'))
CONF['specpath'] = ROOT_DIR
CONF['spec'] = os.path.join(ROOT_DIR, 'dataclean.spec')

datas = [
    ('app/theme.qss', 'app'),
]
datas += collect_data_files('matplotlib')

hiddenimports = [
    'matplotlib.backends.backend_qtagg',
    'openpyxl',
    'pyarrow',
    'xlrd',
    'rapidfuzz',
]

a = Analysis(
    ['scripts/launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='DataClean',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='build/version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DataClean',
)
