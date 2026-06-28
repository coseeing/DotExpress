@echo off
setlocal

set "ROOT=%~dp0.."
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

if not defined M4_EXE (
    echo M4_EXE must point to m4.exe.
    exit /b 1
)

pushd "%ROOT%"
scons M4_EXE="%M4_EXE%" %*
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
