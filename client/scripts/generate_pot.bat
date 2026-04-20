@echo off
setlocal EnableDelayedExpansion

set FILES=brailleTables\__tables.py
for %%f in (*.py) do (
    set FILES=!FILES! %%f
)

xgettext --language=Python --keyword=_ --output=locales\dotexpress.pot !FILES!
