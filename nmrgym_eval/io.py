"""Strict JSONL alignment and run provenance."""

import hashlib
import json
from pathlib import Path
import platform
from importlib.metadata import PackageNotFoundError, version


def read_json(path):
    def reject_constant(value):
        raise ValueError(f"Non-standard JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant)


def records(path):
    result = {}
    with open(path, encoding="utf-8") as handle:
        for line, text in enumerate(handle, 1):
            if not text.strip():
                continue
            row = json.loads(text, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {v}")))
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                raise ValueError(f"{path}:{line}: each row needs a nonempty string id")
            if row["id"] in result:
                raise ValueError(f"{path}:{line}: duplicate id {row['id']}")
            result[row["id"]] = row
    if not result:
        raise ValueError(f"{path}: empty input")
    return result


def aligned(target_path, prediction_path):
    target, predicted = records(target_path), records(prediction_path)
    if target.keys() != predicted.keys():
        raise ValueError(f"ID sets differ: {len(target.keys() - predicted.keys())} missing, {len(predicted.keys() - target.keys())} extra predictions")
    return list(target.values()), [predicted[k] for k in target]


def labels(path):
    names = read_json(path)
    if not isinstance(names, list) or not names or any(not isinstance(v, str) or not v for v in names) or len(set(names)) != len(names):
        raise ValueError("Label schema must be a JSON list of unique nonempty names in column order")
    return names


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance(paths):
    packages = {}
    for package in ("numpy", "scipy", "rdkit"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            pass
    return {"python": platform.python_version(), "packages": packages,
            "inputs": {key: {"path": str(path), "sha256": digest(path)} for key, path in paths.items() if path}}


def write_json(path, value):
    content = json.dumps(value, indent=2, allow_nan=False) + "\n"
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
    else:
        print(content, end="")
