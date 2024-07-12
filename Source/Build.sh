#!/bin/bash

python=python3

$python -m pip install --upgrade pip
$python -m pip install --upgrade pyinstaller

# Install dependencies
$python -m pip install --upgrade websockets
$python -m pip install --upgrade cefpython3

# Create the executable
# Uncomment and adjust the line below if you want to specify options for PyInstaller
# $python -m PyInstaller --onefile --clean --additional-hooks-dir=. --icon=SHTS.ico --add-data "SHTS.ico:." SHTS.py
$python pyinstaller.py

# Copy the output
cp -r dist/SHTS ../SHTS/MAC