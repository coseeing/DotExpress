@echo off
pushd "%~dp0..\client"
pyinstaller --onefile --name=DotExpress ^
--noconsole ^
--add-data "braille/liblouis.dll;braille" ^
--add-data "braille/liblouis/tables;braille/liblouis/tables" ^
--add-data "mathcat/assets;mathcat/assets" ^
--add-data "data;data" ^
--add-data "locales;locales" ^
--collect-data "latex2mathml" ^
gui.py
popd
