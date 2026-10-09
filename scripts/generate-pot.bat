@echo off
setlocal EnableDelayedExpansion

rem Usage: scripts\generate-pot.bat [output.pot]
rem Writes client\locales\dotexpress.pot unless another output path is given.
rem Source references are relative to client\ with forward slashes, in sorted
rem file order, so every checkout produces the same template.

pushd "%~dp0..\client"
set "OUTPUT=%~1"
if not defined OUTPUT set "OUTPUT=locales\dotexpress.pot"
set "CLIENT_DIR=%CD%\"
set "FILE_LIST=%TEMP%\dotexpress-xgettext-%RANDOM%.txt"

>"%FILE_LIST%.all" (
    for /r %%f in (*.py) do (
        set "SOURCE=%%f"
        set "SOURCE=!SOURCE:%CLIENT_DIR%=!"
        echo(!SOURCE:\=/!
    )
)
findstr /v /i /b /l /c:".venv/" /c:"tests/" /c:"build/" /c:"dist/" "%FILE_LIST%.all" | "%SystemRoot%\System32\sort.exe" /l C /o "%FILE_LIST%"

xgettext --language=Python --keyword=_ --keyword=N_ --files-from="%FILE_LIST%" --from-code=UTF-8 --output="%OUTPUT%"
set "STATUS=%ERRORLEVEL%"
del "%FILE_LIST%.all" "%FILE_LIST%"
popd
exit /b %STATUS%
