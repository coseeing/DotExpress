#!/bin/bash
# Run the F-18 GUI items one after the other (each through run_item.sh, one heavy job at a time).
# Usage: run_all.sh [round suffix]  (the suffix goes into each label, so that a rerun gets new folders)
HERE=$(cd "$(dirname "$0")" && pwd)
R=${1:-}
cd "$HERE"
bash run_item.sh "146${R}" item146.py new
bash run_item.sh "147${R}" item147.py new
# 147 on N-f14b ran once already (auto147-f14b-f18); the old build does not change.
bash run_item.sh "149${R}" item149.py new
bash run_item.sh "152${R}" item152.py new
bash run_item.sh "154${R}" item154.py new
bash run_item.sh "156${R}" item156.py new
bash run_item.sh "157${R}" item157.py new
bash run_item.sh "158${R}" item158.py new
bash run_item.sh "158${R}" item158.py old
echo "all items done"
