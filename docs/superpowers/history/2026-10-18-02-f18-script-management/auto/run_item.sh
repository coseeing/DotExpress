#!/bin/bash
# Usage: run_item.sh <label> <script> <build: fix|new|first|old> [script args...]
# label names the folder and the log: D:\dxtest\auto<label>-f18c (N-f18c, the build of the
# review fixes), auto<label>-f18b (N-f18b, the build that was reviewed),
# auto<label>-f18 (N-f18, the build before the editor label fix) or auto<label>-f14b-f18
# (N-f14b, the build before F-18); script is a path relative to this folder.
# Refuses a folder that is not D:\dxtest\auto*-f18 or one that exists, stops if C: has less
# than 2 GB free, waits until 600 MB of memory are available, then runs the script through
# F-13's safe_run.py (keys only to the app under test in the foreground). Afterwards it ends
# only processes under the item's folder and removes only the %TEMP%\_MEI* folders that
# F-13's mei_poll.ps1 saw this item's processes load.
HERE=$(cd "$(dirname "$0")" && pwd)
F13="$HERE/../../2026-10-14-02-f13-behavior-nvda/auto"
UIA=${UIA:-/c/Users/tseng/AppData/Local/Temp/claude/D--workspace-DotExpress/0b4f3b5f-e5f4-4ab9-ac1d-e0bf74afa4a1/scratchpad/uia/Scripts/python.exe}
LABEL=$1; SCRIPT=$2; BUILD=$3; shift 3
case "$BUILD" in
  fix) EXE='D:\dxtest\N-f18c\DotExpress.exe'; SUF=-f18c ;;
  new) EXE='D:\dxtest\N-f18b\DotExpress.exe'; SUF=-f18b ;;
  first) EXE='D:\dxtest\N-f18\DotExpress.exe'; SUF=-f18 ;;
  old) EXE='D:\dxtest\N-f14b\DotExpress.exe'; SUF=-f14b-f18 ;;
  *) echo "build must be fix, new, first or old"; exit 2 ;;
esac
NAME="auto${LABEL}${SUF}"
FOLDER=$(cygpath -w "/d/dxtest/${NAME}")
LOG="/d/dxtest/${NAME}.log"
case "$FOLDER" in
  'D:\dxtest\auto'*'-f18'|'D:\dxtest\auto'*'-f18b'|'D:\dxtest\auto'*'-f18c') echo "folder ${FOLDER} exe ${EXE}" ;;
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
cd "$HERE"
MEI_LIST="/d/dxtest/${NAME}.mei"; MEI_STOP="/d/dxtest/${NAME}.mei-stop"
rm -f "$MEI_LIST" "$MEI_STOP"
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$F13/mei_poll.ps1")" "$FOLDER" "$(cygpath -w "$MEI_LIST")" "$(cygpath -w "$MEI_STOP")" &
POLL=$!
"$UIA" -X utf8 "$F13/safe_run.py" "$SCRIPT" "$EXE" "$FOLDER" "$@" > "$LOG" 2>&1
echo "exit $? mem $MEM C: ${FREE} MB" >> "$LOG"
cat "$LOG"
# Clean up after a script that stopped early: only processes of this item's folder.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ? { \$_.CommandLine -like '*lockshare.py*${NAME}*' -or \$_.ExecutablePath -like '${FOLDER}\*' } | % { Stop-Process -Id \$_.ProcessId -Force }" > /dev/null 2>&1
touch "$MEI_STOP"; wait "$POLL"
# Remove the listed folders that no running DotExpress process uses.
if [ -s "$MEI_LIST" ]; then
  powershell -NoProfile -Command "\$used = @(Get-Process DotExpress -ErrorAction SilentlyContinue | ForEach-Object { \$_.Modules } | ForEach-Object { \$_.FileName }); Get-Content -LiteralPath '$(cygpath -w "$MEI_LIST")' | Sort-Object -Unique | Where-Object { (Split-Path \$_ -Leaf) -like '_MEI*' -and (Test-Path -LiteralPath \$_) } | Where-Object { \$p = \$_ + '\'; -not (\$used | Where-Object { \$_.StartsWith(\$p) }) } | ForEach-Object { Write-Output ('removed ' + (Split-Path \$_ -Leaf)); Remove-Item -LiteralPath \$_ -Recurse -Force -ErrorAction SilentlyContinue }"
fi
echo "mei folders of this item: $(sort -u "$MEI_LIST" 2>/dev/null | wc -l)"
rm -f "$MEI_STOP"
