#!/bin/bash
# Usage: run_item.sh <label> <script> <build: new|old> [script args...]
# label names the folder and the log (D:\dxtest\auto<label>-f13 or auto<label>-f12b-f13);
# script is a path relative to this folder (earlier items: ../../<folder>/auto/<script>).
# Waits until 600 MB of memory are available, then runs the script through safe_run.py.
HERE=$(cd "$(dirname "$0")" && pwd)
UIA=${UIA:-/c/Users/tseng/AppData/Local/Temp/claude/D--workspace-DotExpress/42777709-a544-41aa-bed0-c5bd95d5cfd9/scratchpad/uia/Scripts/python.exe}
LABEL=$1; SCRIPT=$2; BUILD=$3; shift 3
case "$BUILD" in
  new) EXE='D:\dxtest\N-f13\DotExpress.exe'; SUF=-f13 ;;
  old) EXE='D:\dxtest\N-f12b\DotExpress.exe'; SUF=-f12b-f13 ;;
  *) echo "build must be new or old"; exit 2 ;;
esac
NAME="auto${LABEL}${SUF}"
FOLDER=$(cygpath -w "/d/dxtest/${NAME}")
LOG="/d/dxtest/${NAME}.log"
while true; do
  MEM=$(powershell -NoProfile -Command "[int](Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue" | tr -d '\r')
  if [ "$MEM" -ge 600 ]; then break; fi
  sleep 15
done
export PYTHONIOENCODING=utf-8
STARTED=$(date "+%Y-%m-%dT%H:%M:%S")
cd "$HERE"
"$UIA" -X utf8 safe_run.py "$SCRIPT" "$EXE" "$FOLDER" "$@" > "$LOG" 2>&1
echo "exit $? mem $MEM" >> "$LOG"
cat "$LOG"
# Clean up after a script that stopped early: only processes of this item's folder.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ? { \$_.CommandLine -like '*lockshare.py*${NAME}*' -or \$_.ExecutablePath -like '${FOLDER}\*' } | % { Stop-Process -Id \$_.ProcessId -Force }" > /dev/null 2>&1
# The onefile exe unpacks itself into %TEMP%\_MEI<n>; a process that is ended (or ends with
# the session messages) leaves that folder behind (about 100 MB each). Remove the ones this item
# made: created since it started, holding DotExpress's mathcat folder, and not in use by any
# running DotExpress process.
powershell -NoProfile -Command "\$since = [datetime]'${STARTED}'; \$used = @(Get-Process DotExpress -ErrorAction SilentlyContinue | ForEach-Object { \$_.Modules } | ForEach-Object { \$_.FileName }); Get-ChildItem \$env:TEMP -Directory -Filter '_MEI*' | Where-Object { \$_.CreationTime -ge \$since -and (Test-Path (Join-Path \$_.FullName 'mathcat')) } | Where-Object { \$p = \$_.FullName + '\'; -not (\$used | Where-Object { \$_.StartsWith(\$p) }) } | ForEach-Object { Remove-Item -LiteralPath \$_.FullName -Recurse -Force -ErrorAction SilentlyContinue }" > /dev/null 2>&1
