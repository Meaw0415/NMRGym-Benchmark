"""Export reference JSONL from NMRGym list-of-dictionaries pickle files.

The restricted reader accepts builtins and the NumPy array constructors used by
the published files; arbitrary pickle globals are rejected.
"""

import argparse
import json
import pickle
from pathlib import Path

import numpy as np

from .io import digest, labels, provenance, write_json
from .metrics import finite_vector


class ArrayUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {
            ("numpy", "dtype"), ("numpy", "ndarray"),
            ("numpy.core.multiarray", "_reconstruct"), ("numpy._core.multiarray", "_reconstruct"),
            ("numpy.core.multiarray", "scalar"), ("numpy._core.multiarray", "scalar"),
            ("numpy.core.numeric", "_frombuffer"), ("numpy._core.numeric", "_frombuffer"),
        }
        if (module, name) not in allowed:
            raise ValueError(f"Unsupported pickle global: {module}.{name}")
        return super().find_class(module, name)


def export(source, *, task, id_prefix, label_schema=None, nucleus=None):
    with open(source, "rb") as handle:
        data = ArrayUnpickler(handle).load()
    if not isinstance(data, list) or not data:
        raise ValueError("Expected a nonempty list of dictionaries")
    names = labels(label_schema) if label_schema else None
    if task in ("functional-groups", "toxicity") and names is None:
        raise ValueError("Classification export requires --labels in the source column order")
    if task == "spectra" and nucleus not in ("1H", "13C"):
        raise ValueError("Spectra export requires --nucleus 1H or 13C")
    source_hash = digest(source)
    rows = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Row {index} is not a dictionary")
        row = {"id": f"{id_prefix}:{index}", "source_row": index}
        if task == "structure":
            smi = item["smiles"]
            if not isinstance(smi, str) or not smi.strip():
                raise ValueError(f"Invalid SMILES field at row {index}")
            row["smiles"] = smi
        elif task == "spectra":
            row["peaks"] = finite_vector(item["h_shift" if nucleus == "1H" else "c_shift"], f"peaks at row {index}").tolist()
        else:
            values = np.asarray(item["fg_onehot" if task == "functional-groups" else "toxicity"], dtype=float)
            if values.shape != (len(names),):
                raise ValueError(f"Label/schema width differs at row {index}")
            # Null denotes missing. Sentinel values such as -1 are rejected;
            # their interpretation belongs in the caller's data preparation.
            if np.isinf(values).any() or not np.isin(values[~np.isnan(values)], [0, 1]).all():
                raise ValueError(f"Labels at row {index} must be binary or null")
            row["labels"] = [None if np.isnan(v) else int(v) for v in values]
        rows.append(row)
    return rows, {"source_sha256": source_hash, "n_samples": len(rows), "task": task,
                  "id_prefix": id_prefix, "labels": names, "nucleus": nucleus,
                  "provenance": provenance({"source": source, "labels": label_schema})}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--task", required=True, choices=("structure", "functional-groups", "toxicity", "spectra"))
    p.add_argument("--id-prefix", required=True, help="Stable split-specific prefix, e.g. nmrgym-test")
    p.add_argument("--labels", help="JSON label names in source column order")
    p.add_argument("--nucleus", choices=("1H", "13C"))
    a = p.parse_args()
    try:
        if not a.id_prefix.strip():
            raise ValueError("id-prefix must be nonempty")
        if Path(a.input).resolve() == Path(a.output).resolve():
            raise ValueError("Output must not overwrite the input")
        rows, manifest = export(a.input, task=a.task, id_prefix=a.id_prefix, label_schema=a.labels, nucleus=a.nucleus)
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        with open(a.output, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, allow_nan=False) + "\n")
        write_json(a.output + ".manifest.json", manifest)
    except (ValueError, TypeError, KeyError, OSError, pickle.UnpicklingError) as exc:
        p.exit(2, f"Export error: {exc}\n")


if __name__ == "__main__":
    main()
