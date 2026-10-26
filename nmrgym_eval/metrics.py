"""Metrics from arXiv:2601.15763v1, Section 3.3 (equations 1--6).

Protocol choices not fixed by an equation are supplied by the caller. Scores
are fractions, not percentages. Input validation deliberately rejects NaNs.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment


def finite_vector(values, name="vector", *, nonempty=True):
    a = np.asarray(values, dtype=float)
    if a.ndim != 1 or (nonempty and not a.size) or not np.isfinite(a).all():
        raise ValueError(f"{name} must be a finite 1D array")
    return a


def binary_matrix(values, name="labels", *, missing):
    a = np.asarray(values, dtype=float)
    if a.ndim != 2 or 0 in a.shape or np.isinf(a).any():
        raise ValueError(f"{name} must be a nonempty 2D matrix")
    observed = ~np.isnan(a)
    if missing not in ("reject", "mask"):
        raise ValueError("missing must be reject or mask")
    if missing == "reject" and not observed.all():
        raise ValueError(f"{name} contains missing labels")
    if not np.isin(a[observed], [0, 1]).all():
        raise ValueError(f"{name} must contain 0/1 (or null with missing=mask)")
    if not observed.any(axis=0).all():
        raise ValueError("Each label must have at least one observed target")
    return a, observed


def multilabel_metrics(targets, predictions, *, missing, zero_division):
    """Positive-class F1/recall; accuracy includes both true positives/negatives.

    With masking, macro averages per-label values and micro pools observed
    entries. Subset accuracy is defined only on fully observed rows.
    """
    if zero_division not in (0, 1):
        raise ValueError("zero_division must be 0 or 1")
    y, mask = binary_matrix(targets, missing=missing)
    p, _ = binary_matrix(predictions, "predictions", missing="reject")
    if y.shape != p.shape:
        raise ValueError("Label/prediction shapes differ")
    tp = ((y == 1) & (p == 1) & mask).sum(axis=0)
    fp = ((y == 0) & (p == 1) & mask).sum(axis=0)
    fn = ((y == 1) & (p == 0) & mask).sum(axis=0)
    tn = ((y == 0) & (p == 0) & mask).sum(axis=0)

    def divide(a, b):
        a, b = np.broadcast_arrays(a, b)
        return np.divide(a, b, out=np.full(a.shape, float(zero_division)), where=b != 0)

    rec = divide(tp, tp + fn)
    f1 = divide(2 * tp, 2 * tp + fp + fn)
    acc = (tp + tn) / mask.sum(axis=0)
    complete = mask.all(axis=1)
    return {
        "n_samples": len(y), "n_labels": y.shape[1],
        "n_observed": int(mask.sum()), "n_complete_samples": int(complete.sum()),
        "macro_accuracy": float(acc.mean()),
        "micro_accuracy": float((tp.sum() + tn.sum()) / mask.sum()),
        "macro_recall": float(rec.mean()),
        "micro_recall": float(divide(tp.sum(), tp.sum() + fn.sum())),
        "macro_f1": float(f1.mean()),
        "micro_f1": float(divide(2 * tp.sum(), 2 * tp.sum() + fp.sum() + fn.sum())),
        "subset_accuracy": float((y[complete] == p[complete]).all(axis=1).mean()) if complete.any() else None,
        "per_label": [dict(accuracy=float(a), recall=float(r), f1=float(f),
                           tp=int(t), fp=int(x), fn=int(n), tn=int(z), observed=int(o))
                      for a, r, f, t, x, n, z, o in zip(acc, rec, f1, tp, fp, fn, tn, mask.sum(axis=0))],
    }


def probability_matrix(values):
    a = np.asarray(values, dtype=float)
    if a.ndim != 2 or 0 in a.shape or not np.isfinite(a).all() or ((a < 0) | (a > 1)).any():
        raise ValueError("scores must be a finite 2D probability matrix in [0, 1]")
    return a


def apply_thresholds(scores, thresholds, comparison):
    p = probability_matrix(scores)
    t = finite_vector(thresholds, "thresholds")
    if len(t) != p.shape[1]:
        raise ValueError("One threshold is required per label")
    if comparison == "ge":
        return (p >= t).astype(int)
    if comparison == "gt":
        return (p > t).astype(int)
    raise ValueError("comparison must be ge or gt")


def fit_thresholds(targets, scores, *, missing, zero_division, comparison, tie_break):
    """Maximize each label's validation F1 over all distinct decisions, O(C N log N)."""
    y, mask = binary_matrix(targets, missing=missing)
    p = probability_matrix(scores)
    if y.shape != p.shape:
        raise ValueError("Label/score shapes differ")
    if zero_division not in (0, 1) or comparison not in ("ge", "gt") or tie_break not in ("highest", "lowest"):
        raise ValueError("Invalid threshold fitting policy")
    thresholds = []
    for col in range(y.shape[1]):
        s = p[mask[:, col], col]
        truth = y[mask[:, col], col]
        order = np.argsort(s, kind="stable")
        s, truth = s[order], truth[order]
        unique = np.unique(s)
        if comparison == "ge":
            choices = np.r_[unique, np.nextafter(unique[-1], np.inf)]
            idx = np.searchsorted(s, choices, side="left")
        else:
            choices = np.r_[np.nextafter(unique[0], -np.inf), unique]
            idx = np.searchsorted(s, choices, side="right")
        prefix = np.r_[0, np.cumsum(truth)]
        tp = prefix[-1] - prefix[idx]
        predicted = len(s) - idx
        denom = predicted + prefix[-1]
        f1 = np.divide(2 * tp, denom, out=np.full(len(denom), float(zero_division)), where=denom != 0)
        best = np.flatnonzero(f1 == f1.max())
        thresholds.append(float(choices[best[-1] if tie_break == "highest" else best[0]]))
    return thresholds


def set_similarity(target, prediction, sigma):
    """Equation 6, for equal-sized nonempty peak multisets. Repeats are retained."""
    a = finite_vector(target, "target peaks")
    b = finite_vector(prediction, "predicted peaks")
    if len(a) != len(b):
        raise ValueError("Set similarity requires equal peak counts; supply an explicit upstream matching protocol for unequal counts")
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("sigma must be positive")
    cost = np.abs(a[:, None] - b[None, :])
    rows, cols = linear_sum_assignment(cost)
    return float(np.exp(-cost[rows, cols].mean() / sigma))


def gaussian_vector(peaks, grid, sigma):
    peaks = finite_vector(peaks, "peaks")
    grid = finite_vector(grid, "grid")
    if len(grid) < 2 or not (np.diff(grid) > 0).all():
        raise ValueError("grid must contain at least two strictly increasing points")
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("sigma must be positive")
    # Sum incrementally to bound memory for long peak lists. No deduplication.
    result = np.zeros(len(grid))
    for peak in peaks:
        result += np.exp(-0.5 * ((grid - peak) / sigma) ** 2)
    return result


def cosine_similarity(a, b, *, zero_norm):
    a, b = finite_vector(a), finite_vector(b)
    if a.shape != b.shape:
        raise ValueError("Vector shapes differ")
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        if zero_norm == "error":
            raise ValueError("Cosine similarity is undefined for a zero vector")
        if zero_norm in (0, 1):
            return float(zero_norm)
        raise ValueError("zero_norm must be error, 0, or 1")
    return float(np.clip(a @ b / denom, -1.0, 1.0))


def fingerprint_similarity(a, b, metric, *, zero_norm):
    a, b = finite_vector(a), finite_vector(b)
    if a.shape != (2048,) or b.shape != (2048,) or not np.isin(a, [0, 1]).all() or not np.isin(b, [0, 1]).all():
        raise ValueError("Fingerprints must be 2048-bit vectors")
    if metric == "cosine":
        return cosine_similarity(a, b, zero_norm=zero_norm)
    if metric != "tanimoto":
        raise ValueError("Unknown fingerprint metric")
    intersection = float(a @ b)
    union = float(a.sum() + b.sum() - intersection)
    if union == 0:
        if zero_norm == "error":
            raise ValueError("Tanimoto similarity is undefined for two zero fingerprints")
        return float(zero_norm)
    return intersection / union


def token_accuracy(target, prediction):
    """Position accuracy divided by target token count; caller supplies tokens."""
    if not isinstance(target, list) or not target or not isinstance(prediction, list):
        raise ValueError("Tokens must be lists, with a nonempty reference")
    if any(not isinstance(t, (str, int)) or isinstance(t, bool) for t in target + prediction):
        raise ValueError("Tokens must be strings or integer token IDs")
    return sum(a == b for a, b in zip(target, prediction)) / len(target)
