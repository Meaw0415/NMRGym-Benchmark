#!/usr/bin/env bash
# Run from the repository root after installing requirements-chem.txt.
set -euo pipefail
python -m nmrgym_eval structure \
  --targets examples/structure.targets.jsonl \
  --predictions examples/structure.predictions.jsonl \
  --top-k 1 5 10 --match raw --invalid zero \
  --fingerprint-config examples/fingerprints.json \
  --topk-reduction best --zero-norm 0 --tokens \
  --output results/structure.json
for task in functional-groups toxicity; do
  python -m nmrgym_eval "$task" \
    --targets examples/classification.targets.jsonl \
    --predictions examples/classification.predictions.jsonl \
    --labels examples/labels.json --missing-labels reject --zero-division 0 \
    --output "results/${task}.json"
done
python -m nmrgym_eval fit-thresholds \
  --targets examples/validation.targets.jsonl \
  --predictions examples/validation.scores.jsonl \
  --labels examples/labels.json --split validation \
  --missing-labels reject --zero-division 0 \
  --comparison ge --tie-break highest --output results/thresholds.json
python -m nmrgym_eval functional-groups \
  --targets examples/classification.targets.jsonl \
  --predictions examples/classification.scores.jsonl \
  --labels examples/labels.json --missing-labels reject --zero-division 0 \
  --thresholds results/thresholds.json --output results/classification.scores.json
for nucleus in 1H 13C; do
  python -m nmrgym_eval spectra \
    --targets examples/spectra.targets.jsonl \
    --predictions examples/spectra.predictions.jsonl \
    --nucleus "$nucleus" --unavailable exclude \
    --grid examples/grid.json --zero-norm error \
    --output "results/spectra.${nucleus}.json"
done
