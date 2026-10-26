# Evaluation data

Download the reference splits from [Hugging Face](https://huggingface.co/datasets/meaw0415/NMRGym).
[The evaluation guide](../docs/EVALUATION.md#reference-data) provides a versioned
test download, SHA-256 verification, and export commands for all four tasks.
Keep downloaded files and generated JSONL under `data/local/` (git-ignored).

The evaluator reads UTF-8 JSONL, with one object per sample and a unique string
`id`. References and predictions are separate files joined by ID, not by row
order. All reference IDs must have prediction records.

| Task | Reference fields | Prediction fields |
| --- | --- | --- |
| Structure | `id`, `smiles`; optional `tokens` | `id`, ranked `candidates`; optional `candidate_tokens` |
| Functional groups | `id`, `labels` | `id`, binary `labels` or probability `scores` |
| Toxicity | `id`, `labels` | `id`, binary `labels` or probability `scores` |
| Spectral simulation, one nucleus per run | `id`, `peaks` in ppm | `id`, `peaks` in ppm; `null`/`[]` for unavailable predictions |

Classification needs an ordered label-name schema. Supplied schemas live in
`configs/`; choose the one matching the source array's column order. See
`examples/` for small synthetic reference/prediction pairs and
[docs/EVALUATION.md](../docs/EVALUATION.md) for score conventions and commands.

`python -m nmrgym_eval.export` converts a NMRGym list-of-dictionaries pickle
to this reference format, retaining row order and peak multiplicities. It
writes a manifest alongside the output with source SHA-256 and export settings.
