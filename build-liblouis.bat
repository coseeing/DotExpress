@echo off
setlocal enabledelayedexpansion

rem Set up the MSVC build environment (x64 Native Tools)
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

if errorlevel 1 (
    echo Failed to load the Visual Studio build environment. Make sure VS 2022 C++ tools are installed.
    exit /b 1
)

set ROOT=%~dp0
set SRC=%ROOT%include\liblouis
set WINDIR=%SRC%\windows
set STATIC_MAKEFILE=%ROOT%build\liblouis-static.nmake

if not exist "%WINDIR%\Makefile.nmake" (
    echo Missing %WINDIR%\Makefile.nmake. Confirm the liblouis sources exist under include\liblouis.
    exit /b 1
)

if not exist "%STATIC_MAKEFILE%" (
    echo Missing %STATIC_MAKEFILE%. Confirm the custom nmake file exists.
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

rem Copy artifacts back to the repository root for consumption
copy /Y "%WINDIR%\liblouis.dll" "%ROOT%liblouis.dll" >nul
copy /Y "%WINDIR%\liblouis.lib" "%ROOT%liblouis.lib" >nul

echo liblouis.dll build complete. Output copied to %ROOT%
endlocal
 
