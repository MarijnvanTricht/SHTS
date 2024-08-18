# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""
This is a PyInstaller spec file.
"""

import os
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import is_module_satisfies

# Constants
DEBUG = os.environ.get("CEFPYTHON_PYINSTALLER_DEBUG", False)

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

import importlib
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
 ("shts.ico", ".")
] 

a = Analysis(
    ["shts.py"],
    hookspath=["."],  # To find "hook-cefpython3.py"
	datas=datas
)

if not os.environ.get("PYINSTALLER_CEFPYTHON3_HOOK_SUCCEEDED", None):
    raise SystemExit("Error: Pyinstaller hook-cefpython3.py script was "
                     "not executed or it failed")

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name="SHTS",
          debug=DEBUG,
          strip=False,
          upx=False,
          console=DEBUG,
          icon="shts.ico")

COLLECT(exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name="SHTS")