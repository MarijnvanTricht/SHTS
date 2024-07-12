@echo off

set python=python

%python% -m pip install --upgrade pip
%python% -m pip install --upgrade pyinstaller

REM Install depencies to script
%python% -m pip install --upgrade websockets
%python% -m pip install --upgrade cefpython3

REM Create the executable
REM %python% -m PyInstaller --onefile --clean --additional-hooks-dir=. --icon=SHTS.ico --add-data "SHTS.ico;." SHTS.py
%python% pyinstaller.py

xcopy "dist/SHTS" "../SHTS/WIN" /s /e /y /i /q