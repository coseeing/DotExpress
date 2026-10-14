#!/bin/bash
# Usage: run_item.sh <label> <script> <build: new|old|newb> [script args...]
# label names the folder and the log (D:\dxtest\auto<label>-f13, auto<label>-f12b-f13, or for the
# review fix phase's build N-f13b auto<label>-f13b);
# script is a path relative to this folder (earlier items: ../../<folder>/auto/<script>).
# Waits until 600 MB of memory are available, then runs the script through safe_run.py.
HERE=$(cd "$(dirname "$0")" && pwd)
UIA=${UIA:-/c/Users/tseng/AppData/Local/Temp/claude/D--workspace-DotExpress/42777709-a544-41aa-bed0-c5bd95d5cfd9/scratchpad/uia/Scripts/python.exe}
LABEL=$1; SCRIPT=$2; BUILD=$3; shift 3
case "$BUILD" in
  new) EXE='D:\dxtest\N-f13\DotExpress.exe'; SUF=-f13 ;;
  old) EXE='D:\dxtest\N-f12b\DotExpress.exe'; SUF=-f12b-f13 ;;
  newb) EXE='D:\dxtest\N-f13b\DotExpress.exe'; SUF=-f13b ;;
  *) echo "build must be new, old or newb"; exit 2 ;;
esac
NAME="auto${LABEL}${SUF}"
FOLDER=$(cygpath -w "/d/dxtest/${NAME}")
LOG="/d/dxtest/${NAME}.log"
# The first round of F-13 ran in a stray D:\dxtest${NAME} folder: refuse anything but D:\dxtest\auto*.
case "$FOLDER" in
  'D:\dxtest\auto'*) ;;
  *) echo "unexpected folder: $FOLDER"; exit 2 ;;
esac
echo "folder $FOLDER exe $EXE"
while true; do
  MEM=$(powershell -NoProfile -Command "[int](Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue" | tr -d '\r')
  if [ "$MEM" -ge 600 ]; then break; fi
  sleep 15
done
export PYTHONIOENCODING=utf-8
cd "$HERE"
# The onefile exe unpacks itself into %TEMP%\_MEI<n> (about 100 MB); a process that is ended (or
# ends with the session messages) leaves that folder behind. mei_poll.ps1 lists the folders that
# this item's processes load, so that only those are removed below.
MEI_LIST="/d/dxtest/${NAME}.mei"; MEI_STOP="/d/dxtest/${NAME}.mei-stop"
rm -f "$MEI_LIST" "$MEI_STOP"
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$HERE/mei_poll.ps1")" "$FOLDER" "$(cygpath -w "$MEI_LIST")" "$(cygpath -w "$MEI_STOP")" &
POLL=$!
"$UIA" -X utf8 safe_run.py "$SCRIPT" "$EXE" "$FOLDER" "$@" > "$LOG" 2>&1
echo "exit $? mem $MEM" >> "$LOG"
cat "$LOG"
# Clean up after a script that stopped early: only processes of this item's folder.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ? { \$_.CommandLine -like '*lockshare.py*${NAME}*' -or \$_.ExecutablePath -like '${FOLDER}\*' } | % { Stop-Process -Id \$_.ProcessId -Force }" > /dev/null 2>&1
touch "$MEI_STOP"; wait "$POLL"
# Remove the listed folders that no running DotExpress process uses.
if [ -s "$MEI_LIST" ]; then
  powershell -NoProfile -Command "\$used = @(Get-Process DotExpress -ErrorAction SilentlyContinue | ForEach-Object { \$_.Modules } | ForEach-Object { \$_.FileName }); Get-Content -LiteralPath '$(cygpath -w "$MEI_LIST")' | Sort-Object -Unique | Where-Object { (Split-Path \$_ -Leaf) -like '_MEI*' -and (Test-Path -LiteralPath \$_) } | Where-Object { \$p = \$_ + '\'; -not (\$used | Where-Object { \$_.StartsWith(\$p) }) } | ForEach-Object { Remove-Item -LiteralPath \$_ -Recurse -Force -ErrorAction SilentlyContinue }" > /dev/null 2>&1
fi
echo "mei folders of this item: $(sort -u "$MEI_LIST" 2>/dev/null | wc -l)"
rm -f "$MEI_STOP"
