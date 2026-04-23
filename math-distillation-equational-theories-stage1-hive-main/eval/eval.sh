#!/usr/bin/env bash
set -euo pipefail
. .venv/bin/activate
python eval/run_eval.py --hide-response > eval/last_stdout.json
python -c '
import json
from pathlib import Path
obj = json.loads(Path("eval/last_result.json").read_text())
wa = obj["weighted_accuracy"]
mp = obj["mean_parse_rate"]
fs = obj["final_score"]
correct = sum(v["correct"] for v in obj["details"]["problem_sets"].values())
total = sum(v["total"] for v in obj["details"]["problem_sets"].values())
print("---")
print(f"final_score:      {fs:.6f}")
print(f"weighted_acc:     {wa:.6f}")
print(f"parse_rate:       {mp:.6f}")
print(f"correct:          {correct}")
print(f"total:            {total}")
'
