@echo off
setlocal EnableDelayedExpansion

pushd "%~dp0..\client"
set "FILE_LIST=%TEMP%\dotexpress-xgettext-%RANDOM%.txt"
>"%FILE_LIST%" (
    for /r %%f in (*.py) do (
        echo %%f | findstr /i /c:"\.venv\" /c:"\tests\" >nul
        if errorlevel 1 echo %%f
    )
)

xgettext --language=Python --keyword=_ --files-from="%FILE_LIST%" --output=locales\dotexpress.pot
del "%FILE_LIST%"
popd
