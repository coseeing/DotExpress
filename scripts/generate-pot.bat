@echo off
setlocal EnableDelayedExpansion

pushd "%~dp0..\client"
set FILES=braille\tables\__tables.py
for %%f in (*.py) do (
    set FILES=!FILES! %%f
)

xgettext --language=Python --keyword=_ --output=locales\dotexpress.pot !FILES!
popd
