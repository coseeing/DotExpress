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

pushd "%ROOT%"

if not exist "vendor\nvda\liblouis\build\liblouis.h" (
    echo Missing vendor\nvda\liblouis\build\liblouis.h. Run scripts\build-liblouis.bat first.
    popd
    exit /b 1
)

set "TRACE_I=%ROOT%\liblouis-include-trace.i"
set "TRACE_LOG=%ROOT%\liblouis-include-trace.log"

del /q "%TRACE_I%" "%TRACE_LOG%" 2>nul

echo Writing preprocessed output to %TRACE_I%
clang-cl /nologo /E ^
    /Ivendor\nvda\liblouis\build ^
    /Iinclude\liblouis\liblouis ^
    /Iinclude ^
    /Iinclude\wil\include ^
    /ImiscDeps\include ^
    /D_CRT_SECURE_NO_DEPRECATE ^
    /D_WIN32_WINNT=_WIN32_WINNT_WIN10 ^
    /DNOMINMAX ^
    /DNDEBUG ^
    /D_CRT_NONSTDC_NO_DEPRECATE ^
    /DPACKAGE_VERSION=\"3.37.0\" ^
    /DWIDECHARS_ARE_UCS4 ^
    /D_EXPORTING ^
    include\liblouis\liblouis\compileTranslationTable.c > "%TRACE_I%" 2>&1
if errorlevel 1 (
    echo Preprocessor output generation failed.
    popd
    exit /b 1
)

echo Writing include trace to %TRACE_LOG%
clang-cl /nologo /E /showIncludes ^
    /Ivendor\nvda\liblouis\build ^
    /Iinclude\liblouis\liblouis ^
    /Iinclude ^
    /Iinclude\wil\include ^
    /ImiscDeps\include ^
    /D_CRT_SECURE_NO_DEPRECATE ^
    /D_WIN32_WINNT=_WIN32_WINNT_WIN10 ^
    /DNOMINMAX ^
    /DNDEBUG ^
    /D_CRT_NONSTDC_NO_DEPRECATE ^
    /DPACKAGE_VERSION=\"3.37.0\" ^
    /DWIDECHARS_ARE_UCS4 ^
    /D_EXPORTING ^
    include\liblouis\liblouis\compileTranslationTable.c > "%TRACE_LOG%" 2>&1
if errorlevel 1 (
    echo Include trace generation failed.
    popd
    exit /b 1
)

echo --- preprocessed output lines for lou_freeTableFiles / lou_findTables / lou_listTables ---
findstr /n /i "lou_freeTableFiles lou_findTables lou_listTables" "%TRACE_I%"
echo --- include trace lines mentioning liblouis.h ---
findstr /n /i "liblouis.h" "%TRACE_LOG%"

popd
exit /b 0
