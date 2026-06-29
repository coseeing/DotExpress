@echo off
setlocal

set "ROOT=%~dp0.."
set "CLIENT=%ROOT%\client"

if exist "%CLIENT%\dist" rmdir /s /q "%CLIENT%\dist"
if exist "%CLIENT%\build" rmdir /s /q "%CLIENT%\build"
if exist "%CLIENT%\DotExpress.spec" del /q "%CLIENT%\DotExpress.spec"

pushd "%ROOT%"
call scripts\clean-liblouis.bat
if errorlevel 1 (
    set "RESULT=%ERRORLEVEL%"
    popd
    exit /b %RESULT%
)

call scripts\build-liblouis.bat
if errorlevel 1 (
    set "RESULT=%ERRORLEVEL%"
    popd
    exit /b %RESULT%
)

call scripts\install-liblouis.bat
if errorlevel 1 (
    set "RESULT=%ERRORLEVEL%"
    popd
    exit /b %RESULT%
)

call scripts\build-dotexpress.bat
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
