#!/bin/bash
# Usage: run_item.sh <label> <script> <build: new|old> [script args...]
# label names the folder and the log (D:\dxtest\auto<label>-f14 or auto<label>-f12b-f14);
# script is a path relative to this folder (an earlier item: ../../<folder>/auto/<script>).
# Waits until 600 MB of memory are available, stops if C: has less than 2 GB free or the
# folder name is not the expected one, then runs the script through safe_run.py.
HERE=$(cd "$(dirname "$0")" && pwd)
UIA=${UIA:-/c/Users/tseng/AppData/Local/Temp/claude/D--workspace-DotExpress/42777709-a544-41aa-bed0-c5bd95d5cfd9/scratchpad/uia/Scripts/python.exe}
LABEL=$1; SCRIPT=$2; BUILD=$3; shift 3
case "$BUILD" in
  new) EXE='D:\dxtest\N-f14\DotExpress.exe'; SUF=-f14 ;;
  old) EXE='D:\dxtest\N-f12b\DotExpress.exe'; SUF=-f12b-f14 ;;
  *) echo "build must be new or old"; exit 2 ;;
esac
NAME="auto${LABEL}${SUF}"
FOLDER=$(cygpath -w "/d/dxtest/${NAME}")
LOG="/d/dxtest/${NAME}.log"
case "$FOLDER" in
  'D:\dxtest\auto'*'-f14') echo "folder ${FOLDER}" ;;
  *) echo "unexpected folder '${FOLDER}'; nothing was run"; exit 2 ;;
esac
if [ -e "/d/dxtest/${NAME}" ]; then echo "${FOLDER} exists already; nothing was run"; exit 2; fi
FREE=$(powershell -NoProfile -Command "[int]((Get-PSDrive C).Free/1MB)" | tr -d '\r')
if [ "$FREE" -lt 2048 ]; then echo "C: has ${FREE} MB free; nothing was run"; exit 3; fi
while true; do
  MEM=$(powershell -NoProfile -Command "[int](Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue" | tr -d '\r')
  if [ "$MEM" -ge 600 ]; then break; fi
  sleep 15
done
export PYTHONIOENCODING=utf-8
STARTED=$(date "+%Y-%m-%dT%H:%M:%S")
cd "$HERE"
"$UIA" -X utf8 safe_run.py "$SCRIPT" "$EXE" "$FOLDER" "$@" > "$LOG" 2>&1
echo "exit $? mem $MEM C: ${FREE} MB" >> "$LOG"
cat "$LOG"
# Clean up after a script that stopped early: only processes of this item's folder.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ? { \$_.CommandLine -like '*lockshare.py*${NAME}*' -or \$_.ExecutablePath -like '${FOLDER}\*' } | % { Stop-Process -Id \$_.ProcessId -Force }" > /dev/null 2>&1
# The onefile exe unpacks itself into %TEMP%\_MEI<n> (about 100 MB) and leaves it behind when
# it is ended. Remove the ones this item made: created since it started, holding DotExpress's
# mathcat folder, and not in use by any running DotExpress process. Older ones stay.
powershell -NoProfile -Command "\$since = [datetime]'${STARTED}'; \$used = @(Get-Process DotExpress -ErrorAction SilentlyContinue | ForEach-Object { \$_.Modules } | ForEach-Object { \$_.FileName }); Get-ChildItem \$env:TEMP -Directory -Filter '_MEI*' | Where-Object { \$_.CreationTime -ge \$since -and (Test-Path (Join-Path \$_.FullName 'mathcat')) } | Where-Object { \$p = \$_.FullName + '\'; -not (\$used | Where-Object { \$_.StartsWith(\$p) }) } | ForEach-Object { Write-Output ('removed ' + \$_.Name); Remove-Item -LiteralPath \$_.FullName -Recurse -Force -ErrorAction SilentlyContinue }"
