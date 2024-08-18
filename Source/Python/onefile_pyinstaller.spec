# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""
This is a PyInstaller spec file.
"""

import os
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import is_module_satisfies
import importlib

# Constants
DEBUG = os.environ.get("CEFPYTHON_PYINSTALLER_DEBUG", False)

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def get_cefpython_path():
    # Find the spec of the cefpython module
    spec = importlib.util.find_spec('cefpython3')
    if spec is None:
        raise ImportError('cefpython3 module not found')
    
    # Get the module file path
    module_path = spec.origin
    if module_path is None:
        raise ImportError('Unable to determine the path of the cefpython3 module')
    
    # Return the directory containing the module
    return os.path.dirname(module_path)

# Usage
try:
    cef = get_cefpython_path()
except ImportError as e:
    print(e)

datas = [
    ("%s/icudtl.dat" % cef, "cefpython3"),
    ("%s/natives_blob.bin" % cef, "cefpython3"),
    ("%s/cef.pak" % cef, "cefpython3"),
    ("%s/cef_100_percent.pak" % cef, "cefpython3"),
    ("%s/cef_200_percent.pak" % cef, "cefpython3"),
    ("%s/cef_extensions.pak" % cef, "cefpython3"),
    ("%s/locales/en-US.pak" % cef, "cefpython3/locales"),
    ("shts.ico", ".")  # Add the icon to the data files
]

a = Analysis(
    ["shts.py"],
    hookspath=["."],  # To find "hook-cefpython3.py"
    datas=datas,
    binaries=[],
    hiddenimports=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

if not os.environ.get("PYINSTALLER_CEFPYTHON3_HOOK_SUCCEEDED", None):
    raise SystemExit("Error: Pyinstaller hook-cefpython3.py script was "
                     "not executed or it failed")

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SHTS",
    debug=DEBUG,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=DEBUG,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="shts.ico"
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="SHTS"
)

app = BUNDLE(
    coll,
    name="SHTS",
    icon="shts.ico",
    bundle_identifier=None,
    info_plist=None,
    additional_paths=[]
)
