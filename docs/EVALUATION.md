# NMRGym evaluation scripts

These commands evaluate saved predictions for the tasks in
[NMRGym, arXiv:2601.15763v1](https://arxiv.org/abs/2601.15763v1), Section 3.3.
Run them from the repository root. They do not require a GPU or run model inference.
All reported scores use fractions; multiply by 100 for percentage columns.

| Command | Metrics | Paper reference |
| --- | --- | --- |
| `structure` | Top-K exact match; optional token accuracy and 2048-bit Morgan, torsion, atom-pair Tanimoto/cosine similarity | Eqs. 1–3; Tables 2, 3, 10 |
| `functional-groups` | Macro/micro accuracy, recall, F1; subset accuracy; per-label confusion counts | Eq. 4; Table 4 |
| `toxicity` | Same multilabel metrics | Eq. 4; Table 5 |
| `spectra` | Coverage, Hungarian set similarity, optional Gaussian-vector cosine similarity | Eqs. 5–6; Table 6 |
| `fit-thresholds` | Per-label validation F1 threshold fitting | Appendix B.5 |

## Installation and tests

Tested with Python 3.12. Dependencies are pinned to the tested evaluator environment.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-chem.txt
python -m unittest discover -s tests -v
bash scripts/evaluate_examples.sh
```

On Windows activate with `.venv\Scripts\activate`. Classification, spectral
evaluation, and reference export need only `requirements-eval.txt`; structure
evaluation also needs RDKit from `requirements-chem.txt`.

## Reference data

The [dataset files](https://huggingface.co/datasets/meaw0415/NMRGym/tree/b1172058c1961d10d3005aec3eec93e5b0e4342e)
include `NMRGym_{train,val,test}_balanced_dedup.pkl`. For a versioned test-file download:

```bash
mkdir -p data/local
curl -L --fail --retry 3 \
  https://huggingface.co/datasets/meaw0415/NMRGym/resolve/b1172058c1961d10d3005aec3eec93e5b0e4342e/NMRGym_test_balanced_dedup.pkl \
  -o data/local/NMRGym_test_balanced_dedup.pkl
python -c "import hashlib; from pathlib import Path; assert hashlib.sha256(Path('data/local/NMRGym_test_balanced_dedup.pkl').read_bytes()).hexdigest() == '04504b08800baf5fab57836e51b9314cc600eff237da6222c4567eec03379ac3'"
```

Export JSONL references, preserving the original row order and repeated peaks:

```bash
python -m nmrgym_eval.export \
  --input data/local/NMRGym_test_balanced_dedup.pkl \
  --task structure --id-prefix nmrgym-test \
  --output data/local/structure.targets.jsonl

python -m nmrgym_eval.export \
  --input data/local/NMRGym_test_balanced_dedup.pkl \
  --task functional-groups --labels configs/labels-fg22.json \
  --id-prefix nmrgym-test --output data/local/fg.targets.jsonl

python -m nmrgym_eval.export \
  --input data/local/NMRGym_test_balanced_dedup.pkl \
  --task toxicity --labels configs/labels-tox7.json \
  --id-prefix nmrgym-test --output data/local/tox.targets.jsonl

python -m nmrgym_eval.export \
  --input data/local/NMRGym_test_balanced_dedup.pkl \
  --task spectra --nucleus 1H --id-prefix nmrgym-test \
  --output data/local/h.targets.jsonl
```

Use `--nucleus 13C` for carbon peaks. Export validation references separately with
`--id-prefix nmrgym-val`. Each export writes a `.manifest.json` with source SHA-256,
sample count, label names, and environment. The exporter uses a restricted NumPy
pickle reader and does not regenerate labels, clean molecules, or split data.

IDs are `PREFIX:ROW_INDEX`, starting at zero. Prediction IDs must come from the
same exported reference file and dataset revision. Evaluation joins on IDs;
reordered rows are accepted, while missing, extra, or duplicate IDs are rejected.
Each test sample must have a prediction record, including failed predictions.

## Structure elucidation

References contain `id` and `smiles`. Predictions contain a ranked `candidates`
list. An empty list represents no candidates. Example:

```json
{"id":"nmrgym-test:0","candidates":["CCO","CCN"]}
```

```bash
python -m nmrgym_eval structure \
  --targets examples/structure.targets.jsonl \
  --predictions examples/structure.predictions.jsonl \
  --top-k 1 5 10 --match raw --invalid zero \
  --output results/structure.json
```

`--match raw` compares supplied SMILES strings directly (Eq. 1).
`canonical-isomeric` canonicalizes with stereochemistry retained;
`canonical-nonisomeric` canonicalizes with stereochemistry omitted. All three
modes validate molecular syntax using RDKit; no salt stripping or tautomer
normalization is performed. Use the matching policy of your evaluation run.
`--invalid zero` retains invalid candidates at their original ranks and scores
them zero; `--invalid error` stops instead. Candidates are never deduplicated or
reranked. Formula conditioning belongs to the model's generation process.

For fingerprints and supplied tokens:

```bash
python -m nmrgym_eval structure \
  --targets examples/structure.targets.jsonl \
  --predictions examples/structure.predictions.jsonl \
  --top-k 1 5 10 --match raw --invalid zero \
  --fingerprint-config examples/fingerprints.json \
  --topk-reduction best --zero-norm 0 --tokens \
  --output results/structure.full.json
```

`examples/fingerprints.json` is an explicit runnable **example configuration**.
Supply your run's RDKit parameters for an experiment comparison. Each selected
generator must specify every supported parameter; fingerprint size is fixed at
2048 bits. RDKit's version and the configuration are saved in the output.

`--topk-reduction best` takes the highest similarity/position accuracy among the
first K candidates. `mean` averages K scores, assigning zero to absent ranks.
Exact match always tests whether any of the first K candidates matches. All
sample-level scores are then averaged over every reference sample.

For `--tokens`, references additionally contain `tokens`, and predictions contain
`candidate_tokens`, one list for each candidate. Supply tokens from your model's
tokenizer with your chosen BOS/EOS/padding treatment already applied. Accuracy
counts matching positions divided by reference length; missing positions are
incorrect and extra predicted positions do not extend that denominator. No
character-based tokenizer is inferred. `--zero-norm error|0|1` selects behavior
for mathematically undefined all-zero fingerprint comparisons.

## Functional groups and toxicity

Both commands use the same interface. Binary references and predictions contain
`id` and a `labels` array. A separate JSON list specifies column names and order.

```bash
python -m nmrgym_eval functional-groups \
  --targets examples/classification.targets.jsonl \
  --predictions examples/classification.predictions.jsonl \
  --labels examples/labels.json --missing-labels reject --zero-division 0 \
  --output results/functional-groups.json
```

Replace `functional-groups` with `toxicity` for toxicity evaluation. Select the
schema matching your supplied arrays:

| Schema | Source of column names/order |
| --- | --- |
| `configs/labels-fg22.json` | Hugging Face dataset card's `fg_onehot` field |
| `configs/labels-tox7.json` | Hugging Face dataset card's `toxicity` field |
| `configs/labels-tox21.json` | Tox21 assay order in paper Appendix D |

Column order must be identical in references, predictions, and thresholds. No
automatic conversion between schemas is performed. Accuracy is the fraction of
correct binary decisions including true negatives; recall and F1 refer to the
positive class. Macro averages per-label scores, while micro pools decisions.
Subset accuracy requires every label in a sample to match (Eq. 4).

`--zero-division 0|1` explicitly selects the value for zero-denominator recall/F1.
`--missing-labels reject` requires complete labels; `mask` accepts JSON `null` in
references and excludes those entries from confusion counts. With masking,
subset accuracy uses only fully observed rows and reports their count; it is
`null` when there are no such rows. Each label must have an observed reference.
Convert dataset-specific missing-value sentinels to `null` before scoring;
nonbinary numeric sentinels are rejected.

### Fit thresholds on validation predictions

Probability prediction records contain `scores` instead of `labels`. Fit each
label's threshold using validation F1 and then freeze it for test evaluation:

```bash
python -m nmrgym_eval fit-thresholds \
  --targets examples/validation.targets.jsonl \
  --predictions examples/validation.scores.jsonl \
  --labels examples/labels.json --split validation \
  --missing-labels reject --zero-division 0 \
  --comparison ge --tie-break highest \
  --output results/thresholds.json

python -m nmrgym_eval functional-groups \
  --targets examples/classification.targets.jsonl \
  --predictions examples/classification.scores.jsonl \
  --labels examples/labels.json --missing-labels reject --zero-division 0 \
  --thresholds results/thresholds.json \
  --output results/functional-groups.scores.json
```

The search considers all distinct validation decision sets, including predicting
none. `ge` uses `score >= threshold`; `gt` uses `score > threshold`.
`highest|lowest` selects among equally optimal thresholds. Boundary thresholds
can lie just outside `[0,1]` to represent all-negative/all-positive decisions.
The artifact records the comparison, label order, and validation input hashes.
Use a separate test split; the CLI rejects reuse of the exact validation target
file as the test target. Dataset split selection remains the caller's responsibility.

## Spectral simulation

Each reference contains `id` and `peaks`, a nonempty list of shifts in ppm.
Predictions use the same format, with `null` or `[]` for an unavailable result.
Evaluate nuclei separately:

```bash
python -m nmrgym_eval spectra \
  --targets examples/spectra.targets.jsonl \
  --predictions examples/spectra.predictions.jsonl \
  --nucleus 1H --unavailable exclude \
  --grid examples/grid.json --zero-norm error \
  --output results/spectra.json
```

Set similarity uses Hungarian minimum absolute-distance matching followed by
`exp(-mean_matched_absolute_error / sigma_set)`, as in Eq. 6. Repeated peaks are
preserved. This implementation scores equal-sized nonempty peak lists; unequal
counts raise an error rather than introduce an unmatched-peak penalty. Perform
any experiment-specific peak matching before supplying the lists.

| Nucleus | `sigma_set` (ppm) | `sigma_vec` (ppm) |
| --- | --- | --- |
| `1H` | 1.0 | 0.3 |
| `13C` | 10.0 | 2.0 |

`--grid` enables vector similarity. Its JSON array supplies the exact increasing
ppm grid used by the caller. The evaluator sums unit-height Gaussians on that
grid and computes cosine similarity (Eq. 5). `examples/grid.json` is a small toy
grid; supply your experiment's grid for scientific evaluation. Omitting `--grid`
computes set similarity only. `--zero-norm` handles vectors with zero norm.
These simulation bandwidths are distinct from the 0.05 ppm classification
preprocessing kernel described in Appendix B.1.

Coverage in this evaluator is the number of nonempty prediction peak lists
divided by the number of reference samples. `--unavailable exclude` averages
similarities over available predictions; `zero` averages over all samples with
unavailable predictions assigned zero. The output always records the coverage,
aggregation policy, scored count, and per-sample scores. An all-unavailable run
with `exclude` reports null similarity, not a fabricated zero.

## Outputs and examples

Every metric output contains input SHA-256 values, package versions, evaluator
version, configuration, and sample counts. No leaderboard files are rewritten.
The files in `examples/` are synthetic inputs for checking the commands:

| Example run | Expected result |
| --- | --- |
| Structure | exact match @1 = 0.5, @5 = @10 = 1.0 |
| Binary classification | macro/micro F1 = 0.5; subset accuracy = 0 |
| Validation thresholds applied to test scores | subset accuracy = 1.0 |
| Proton spectra, excluding unavailable predictions | coverage = 0.5; set similarity = exp(-1) |

The scripts score supplied predictions; generating predictions requires your
model implementation, trained weights, input preprocessing, and generation or
inference settings. Example outputs are checks of the evaluator, not model
benchmark results. To compare repeated runs, retain each run's JSON and apply
your experiment's stated seed set and standard-deviation convention.
