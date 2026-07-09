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

pushd "%ROOT%"
scons install %*
set "RESULT=%ERRORLEVEL%"
popd
if not "%RESULT%"=="0" exit /b %RESULT%

set "MATHCAT_ASSETS_SOURCE=%ROOT%\vendor\nvda\mathcat\assets"
set "MATHCAT_ASSETS=%ROOT%\client\mathcat\assets"

if not exist "%MATHCAT_ASSETS_SOURCE%\libmathcat_py.pyd" (
    echo Missing MathCAT runtime: %MATHCAT_ASSETS_SOURCE%\libmathcat_py.pyd
    exit /b 1
)

if exist "%MATHCAT_ASSETS%" rmdir /s /q "%MATHCAT_ASSETS%"
mkdir "%MATHCAT_ASSETS%"
xcopy "%MATHCAT_ASSETS_SOURCE%\*" "%MATHCAT_ASSETS%\" /E /I /Y >nul
if errorlevel 1 exit /b 1

exit /b %RESULT%
