@echo off
setlocal

set "ROOT=%~dp0.."
set "DIST=%ROOT%\vendor\nvda\liblouis\dist"
set "CLIENT=%ROOT%\client"
set "CLIENT_BRAILLE=%CLIENT%\braille"
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"

if not exist "%VSWHERE%" (
    echo Missing vswhere.exe. Install Visual Studio 2022 C++ Build Tools.
    exit /b 1
)

for /f "usebackq tokens=*" %%I in (`"%VSWHERE%" -latest -version [17.0^,18.0^) -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSROOT=%%I"
if not defined VSROOT (
    echo Visual Studio 2022 C++ tools were not found.
    exit /b 1
)

call "%VSROOT%\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 exit /b 1

where clang-cl >nul 2>&1
if errorlevel 1 (
    echo clang-cl was not found. Install Clang tools for Windows.
    exit /b 1
)

where scons >nul 2>&1
if errorlevel 1 (
    echo scons was not found. Install it with: py -m pip install scons
    exit /b 1
)

pushd "%ROOT%"
if exist "%DIST%" rmdir /s /q "%DIST%"
del /q "%ROOT%\vendor\nvda\liblouis\build\liblouis.h" 2>nul
del /q "%ROOT%\vendor\nvda\liblouis\build\liblouis.dll" "%ROOT%\vendor\nvda\liblouis\build\*.obj" "%ROOT%\vendor\nvda\liblouis\build\*.lib" "%ROOT%\vendor\nvda\liblouis\build\*.exp" "%ROOT%\vendor\nvda\liblouis\build\*.pdb" 2>nul
del /q "%ROOT%\include\liblouis\liblouis\liblouis.h" 2>nul
del /q "%CLIENT_BRAILLE%\liblouis.dll" "%CLIENT_BRAILLE%\liblouis.lib" "%CLIENT_BRAILLE%\liblouis.exp" 2>nul
del /q "%CLIENT_BRAILLE%\louis_helper.py" 2>nul
del /q "%CLIENT_BRAILLE%\liblouis\__init__.py" 2>nul
if exist "%CLIENT_BRAILLE%\liblouis\tables" rmdir /s /q "%CLIENT_BRAILLE%\liblouis\tables"
scons clean-liblouis %*
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
