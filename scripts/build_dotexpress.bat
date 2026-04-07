@echo off
pyinstaller --onefile --name=DotExpress ^
--noconsole ^
--add-data "liblouis.dll;." ^
--add-data "louis/tables;louis/tables" ^
--add-data "data;data" ^
--add-data "locales;locales" ^
gui.py
