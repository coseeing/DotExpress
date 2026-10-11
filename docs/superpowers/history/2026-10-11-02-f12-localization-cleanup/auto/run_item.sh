#!/bin/bash
# Usage: run_item.sh <label> <script> <build: new|before> [prefix] [script args...]
# label: e.g. 109, 110, 114a (names the folder); prefix "autodraft" for drafts.
UIA=/c/Users/tseng/AppData/Local/Temp/claude/D--workspace-DotExpress/450e2986-a576-497a-aa7c-f1429e710d71/scratchpad/uia/Scripts/python.exe
AUTO=/d/workspace/DotExpress-f12/docs/superpowers/history/2026-10-11-02-f12-localization-cleanup/auto
LABEL=$1; SCRIPT=$2; BUILD=$3; PREFIX=${4:-auto}; shift 4
if [ "$BUILD" = new ]; then EXE='D:\dxtest\N-f12\DotExpress.exe'; SUF=-f12; else EXE='D:\dxtest\N-f11c\DotExpress.exe'; SUF=-f11c-f12; fi
FOLDER="D:\\dxtest\\${PREFIX}${LABEL}${SUF}"
LOG="/d/dxtest/${PREFIX}${LABEL}${SUF}.log"
while true; do
  MEM=$(powershell -NoProfile -Command "[int](Get-Counter '\\Memory\\Available MBytes').CounterSamples[0].CookedValue" | tr -d '\r')
  if [ "$MEM" -ge 600 ]; then break; fi
  sleep 15
done
export PYTHONIOENCODING=utf-8
cd "$AUTO"
"$UIA" -X utf8 safe_run.py "$SCRIPT" "$EXE" "$FOLDER" "$@" > "$LOG" 2>&1
echo "exit $? mem $MEM" >> "$LOG"
cat "$LOG"
# Clean up after a script that stopped early: only processes of this item's folder.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ? { \$_.CommandLine -like '*lockshare.py*${PREFIX}${LABEL}${SUF}*' -or \$_.ExecutablePath -like 'D:\dxtest\${PREFIX}${LABEL}${SUF}\*' } | % { Stop-Process -Id \$_.ProcessId -Force }" > /dev/null 2>&1
