@echo off
setlocal enabledelayedexpansion

rem Set up the MSVC build environment (x64 Native Tools)
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

if errorlevel 1 (
    echo Failed to load the Visual Studio build environment. Make sure VS 2022 C++ tools are installed.
    exit /b 1
)

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set "ROOT=%%~fI\"
set CLIENT_DIR=%ROOT%client
set BRAILLE_DIR=%CLIENT_DIR%\braille
set TABLES_DIR=%BRAILLE_DIR%\liblouis\tables
set SRC=%ROOT%include\liblouis
set WINDIR=%SRC%\windows
set SRC_TABLES=%SRC%\tables
set STATIC_MAKEFILE=%ROOT%build\liblouis-static.nmake

if not exist "%SRC%" (
    echo Missing %SRC%.
    echo This repository expects liblouis to be checked out at include\liblouis as a git submodule.
    echo Run: git submodule update --init --recursive
    echo Use a released liblouis tag for the submodule, not master.
    exit /b 1
)

if not exist "%WINDIR%\Makefile.nmake" (
    echo Missing %WINDIR%\Makefile.nmake.
    echo Confirm the liblouis sources were initialized correctly under include\liblouis.
    exit /b 1
)

if not exist "%STATIC_MAKEFILE%" (
    echo Missing %STATIC_MAKEFILE%.
    echo The repository should include build\liblouis-static.nmake. Restore it from git before building.
    exit /b 1
)

if not exist "%SRC_TABLES%" (
    echo Missing %SRC_TABLES%.
    echo Confirm the liblouis source checkout includes the upstream tables directory.
    exit /b 1
)

pushd "%WINDIR%"

rem Always start from a clean slate so stale /MD objects cannot be reused
nmake /f "%STATIC_MAKEFILE%" clean >nul

rem Build liblouis.dll using the custom static CRT makefile
nmake /f "%STATIC_MAKEFILE%"
if errorlevel 1 (
    popd
    echo nmake build failed. Inspect the log for details.
    exit /b 1
)

popd

rem Copy artifacts for packaging/runtime consumption
if exist "%TABLES_DIR%" (
    rmdir /S /Q "%TABLES_DIR%"
)
mkdir "%TABLES_DIR%" >nul 2>&1
if errorlevel 1 (
    echo Failed to create %TABLES_DIR%.
    exit /b 1
)

xcopy /E /I /Y "%SRC_TABLES%\*" "%TABLES_DIR%\" >nul
if errorlevel 1 (
    echo Failed to copy liblouis tables into %TABLES_DIR%.
    exit /b 1
)

copy /Y "%WINDIR%\liblouis.dll" "%BRAILLE_DIR%\liblouis.dll" >nul
if errorlevel 1 (
    echo Failed to copy liblouis.dll into %BRAILLE_DIR%.
    exit /b 1
)

copy /Y "%WINDIR%\liblouis.lib" "%CLIENT_DIR%\liblouis.lib" >nul
if errorlevel 1 (
    echo Failed to copy liblouis.lib into %CLIENT_DIR%.
    exit /b 1
)

echo liblouis build complete. Runtime artifacts copied to %BRAILLE_DIR%
endlocal
 
