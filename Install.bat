@echo off
setlocal

REM Set variables
set "SOURCE_FOLDER=%~dp0SHTS\WIN"
set "TARGET_FOLDER=%AppData%\SHTS"
set "APP_EXECUTABLE=%AppData%\SHTS\SHTS.exe"
set "FILE_EXTENSION=shts"

REM Display variables
echo SOURCE_FOLDER: %SOURCE_FOLDER%
echo TARGET_FOLDER: %TARGET_FOLDER%
echo APP_EXECUTABLE: %APP_EXECUTABLE%
echo FILE_EXTENSION: %FILE_EXTENSION%

REM Check if target directory exists and remove it if it does
if exist "%TARGET_FOLDER%\*" (
    echo Target directory exists. Removing it.
    rd /s /q "%TARGET_FOLDER%"
)

REM Create target directory
mkdir "%TARGET_FOLDER%"

REM Copy folder to AppData
xcopy "%SOURCE_FOLDER%" "%TARGET_FOLDER%" /s /e /y /i /q

echo Folder copied to AppData

REM Create file type and associate with the executable
REM ftype YourAppFileType="%APP_EXECUTABLE% %%1"
REM assoc %FILE_EXTENSION%=YourAppFileType
REM Refresh the file associations
REM assoc %FILE_EXTENSION%

echo .

echo WARNING: File associations are not working
echo This should be added manually

echo .

set TARGET_PATH=%TARGET_FOLDER%\SHTS.exe
set SHORTCUT_NAME=SHTS.lnk
set PROGRAMS_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs
PowerShell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%PROGRAMS_PATH%\%SHORTCUT_NAME%'); $s.TargetPath = '%TARGET_PATH%'; $s.Save()"

echo Shortcut created in the Programs menu

REM Check if TARGET_FOLDER is already in PATH
echo %PATH% | find /i "%TARGET_FOLDER%" >nul
if errorlevel 1 (
    REM Add TARGET_FOLDER to PATH
    echo Adding TARGET_FOLDER to PATH.
    setx PATH "%PATH%;%TARGET_FOLDER%"
)

echo End of install of SHTS

pause
endlocal

