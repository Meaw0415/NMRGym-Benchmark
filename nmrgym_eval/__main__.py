"""Run with python -m nmrgym_eval --help."""

import argparse
import json
from pathlib import Path

import numpy as np

from . import __version__
from .io import aligned, digest, labels, provenance, read_json, write_json
from .metrics import (apply_thresholds, cosine_similarity, finite_vector, fit_thresholds,
                      gaussian_vector, multilabel_metrics, set_similarity)
from .structure import evaluate_structure


def parser():
    p = argparse.ArgumentParser(description="Evaluate NMRGym prediction files (scores in [0,1]).")
    sub = p.add_subparsers(dest="task", required=True)
    for task in ("structure", "functional-groups", "toxicity", "spectra", "fit-thresholds"):
        q = sub.add_parser(task)
        q.add_argument("--targets", required=True, help="Reference JSONL; validation references for fit-thresholds")
        q.add_argument("--predictions", required=True, help="Prediction JSONL, aligned by unique id")
        q.add_argument("--output", help="Write JSON to this path (default: stdout)")
        if task in ("functional-groups", "toxicity", "fit-thresholds"):
            q.add_argument("--labels", required=True, help="JSON list of label names in column order")
            q.add_argument("--missing-labels", choices=("reject", "mask"), required=True)
            q.add_argument("--zero-division", choices=(0, 1), type=int, required=True)
            if task == "fit-thresholds":
                q.add_argument("--comparison", choices=("ge", "gt"), required=True)
                q.add_argument("--tie-break", choices=("highest", "lowest"), required=True)
                q.add_argument("--split", choices=("validation",), required=True)
            else:
                q.add_argument("--thresholds", help="Validation-fitted thresholds JSON; otherwise predictions contain binary labels")
        if task == "structure":
            q.add_argument("--top-k", nargs="+", type=int, default=[1, 5, 10])
            q.add_argument("--match", choices=("raw", "canonical-isomeric", "canonical-nonisomeric"), required=True)
            q.add_argument("--invalid", choices=("error", "zero"), required=True)
            q.add_argument("--fingerprint-config", help="Explicit RDKit generator parameters JSON")
            q.add_argument("--tokens", action="store_true", help="Score supplied token lists; no tokenizer is inferred")
            q.add_argument("--topk-reduction", choices=("best", "mean"))
            q.add_argument("--zero-norm", choices=("error", "0", "1"))
        if task == "spectra":
            q.add_argument("--nucleus", choices=("1H", "13C"), required=True)
            q.add_argument("--unavailable", choices=("exclude", "zero"), required=True,
                           help="Aggregation policy for null/empty prediction peak lists")
            q.add_argument("--grid", help="JSON array of increasing ppm grid points; enables vector similarity")
            q.add_argument("--zero-norm", choices=("error", "0", "1"))
    return p


def zero_norm(value):
    return value if value in (None, "error") else int(value)


def run(args):
    targets, predictions = aligned(args.targets, args.predictions)
    config = {k: v for k, v in vars(args).items() if k not in ("output", "targets", "predictions")}
    paths = {"targets": args.targets, "predictions": args.predictions}
    result = {}
    if args.task in ("functional-groups", "toxicity", "fit-thresholds"):
        names = labels(args.labels)
        paths["labels"] = args.labels
        y = [r["labels"] for r in targets]
        if any(not isinstance(row, list) or len(row) != len(names) for row in y):
            raise ValueError("Target label width must match label schema")
        if args.task == "fit-thresholds":
            scores = [r["scores"] for r in predictions]
            values = fit_thresholds(y, scores, missing=args.missing_labels, zero_division=args.zero_division,
                                    comparison=args.comparison, tie_break=args.tie_break)
            result = {"labels": names, "thresholds": values, "comparison": args.comparison,
                      "split": "validation", "validation_targets_sha256": digest(args.targets)}
        else:
            if args.thresholds:
                paths["thresholds"] = args.thresholds
                artifact = read_json(args.thresholds)
                if artifact.get("labels") != names or artifact.get("split") != "validation":
                    raise ValueError("Threshold artifact must be fitted on validation data with matching label order")
                if artifact.get("validation_targets_sha256") == digest(args.targets):
                    raise ValueError("Evaluation targets are identical to threshold-fitting targets; use a separate test split")
                pred = apply_thresholds([r["scores"] for r in predictions], artifact["thresholds"], artifact["comparison"])
            else:
                pred = [r["labels"] for r in predictions]
            result = multilabel_metrics(y, pred, missing=args.missing_labels, zero_division=args.zero_division)
            result["labels"] = names
            for name, values in zip(names, result["per_label"]):
                values["label"] = name
    elif args.task == "structure":
        fp_config = read_json(args.fingerprint_config) if args.fingerprint_config else None
        if args.fingerprint_config:
            paths["fingerprint_config"] = args.fingerprint_config
        config["fingerprint_parameters"] = fp_config
        result = evaluate_structure(targets, predictions, ks=args.top_k, match=args.match, invalid=args.invalid,
                                    fingerprint_config=fp_config, topk_reduction=args.topk_reduction,
                                    zero_norm=zero_norm(args.zero_norm), score_tokens=args.tokens)
    elif args.task == "spectra":
        sigma_set, sigma_vec = (1.0, 0.3) if args.nucleus == "1H" else (10.0, 2.0)
        config.update(sigma_set_ppm=sigma_set, sigma_vec_ppm=sigma_vec)
        grid = read_json(args.grid) if args.grid else None
        if grid is not None:
            if args.zero_norm is None:
                raise ValueError("Vector similarity requires --zero-norm")
            paths["grid"] = args.grid
            # Validate the grid even when every prediction is unavailable.
            gaussian_vector([0.0], grid, sigma_vec)
        per_sample, available = [], 0
        for target, predicted in zip(targets, predictions):
            truth = finite_vector(target["peaks"], "target peaks")
            peaks = predicted["peaks"]
            if peaks is not None and not isinstance(peaks, list):
                raise ValueError("Predicted peaks must be a list or null")
            ok = peaks is not None and len(peaks) > 0
            row = {"id": target["id"], "available": ok, "set_similarity": None}
            if grid is not None:
                row["vector_similarity"] = None
            if ok:
                pred = finite_vector(peaks, "predicted peaks")
                row["set_similarity"] = set_similarity(truth, pred, sigma_set)
                if grid is not None:
                    row["vector_similarity"] = cosine_similarity(gaussian_vector(truth, grid, sigma_vec),
                                                                  gaussian_vector(pred, grid, sigma_vec),
                                                                  zero_norm=zero_norm(args.zero_norm))
                available += 1
            elif args.unavailable == "zero":
                row["set_similarity"] = 0.0
                if grid is not None:
                    row["vector_similarity"] = 0.0
            per_sample.append(row)
        n_scored = len(targets) if args.unavailable == "zero" else available
        result = {"n_samples": len(targets), "n_available": available, "n_scored": n_scored,
                  "coverage": available / len(targets), "per_sample": per_sample}
        for metric in ["set_similarity"] + (["vector_similarity"] if grid is not None else []):
            values = [r[metric] for r in per_sample if r[metric] is not None]
            result[metric] = float(np.mean(values)) if values else None
    return {"evaluator_version": __version__, "task": args.task, "score_scale": "fraction",
            "config": config, "provenance": provenance(paths), **result}


def main():
    p = parser()
    args = p.parse_args()
    try:
        if args.output:
            inputs = [getattr(args, key, None) for key in ("targets", "predictions", "labels", "thresholds", "grid", "fingerprint_config")]
            if any(Path(path).resolve() == Path(args.output).resolve() for path in inputs if path):
                raise ValueError("Output must not overwrite an input file")
        result = run(args)
        write_json(args.output, result)
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        p.exit(2, f"Evaluation error: {exc}\n")


if __name__ == "__main__":
    main()
