import json
import pickle
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from nmrgym_eval.export import export
from nmrgym_eval.io import aligned, records
from nmrgym_eval.structure import evaluate_structure


ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def cli(self, *args, expected=0):
        r = subprocess.run([sys.executable, "-m", "nmrgym_eval", *map(str, args)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, expected, r.stderr)
        return (json.loads(r.stdout) if r.stdout.strip() else None) if r.returncode == 0 else r.stderr

    def test_examples_all_tasks(self):
        flags = ["--targets", "examples/classification.targets.jsonl", "--predictions", "examples/classification.predictions.jsonl",
                 "--labels", "examples/labels.json", "--missing-labels", "reject", "--zero-division", "0"]
        for task in ("functional-groups", "toxicity"):
            self.assertEqual(self.cli(task, *flags)["macro_f1"], 0.5)
        r = self.cli("spectra", "--targets", "examples/spectra.targets.jsonl", "--predictions", "examples/spectra.predictions.jsonl",
                     "--nucleus", "1H", "--unavailable", "exclude", "--grid", "examples/grid.json", "--zero-norm", "error")
        self.assertEqual(r["coverage"], 0.5)
        self.assertAlmostEqual(r["set_similarity"], np.exp(-1))
        z = self.cli("spectra", "--targets", "examples/spectra.targets.jsonl", "--predictions", "examples/spectra.predictions.jsonl",
                     "--nucleus", "13C", "--unavailable", "zero")
        self.assertAlmostEqual(z["set_similarity"], np.exp(-0.1) / 2)

    def test_fit_then_evaluate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "thresholds.json"
            self.cli("fit-thresholds", "--targets", "examples/validation.targets.jsonl", "--predictions", "examples/validation.scores.jsonl",
                     "--labels", "examples/labels.json", "--missing-labels", "reject", "--zero-division", "0", "--split", "validation",
                     "--comparison", "ge", "--tie-break", "highest", "--output", path)
            r = self.cli("functional-groups", "--targets", "examples/classification.targets.jsonl", "--predictions", "examples/classification.scores.jsonl",
                         "--labels", "examples/labels.json", "--missing-labels", "reject", "--zero-division", "0", "--thresholds", path)
            self.assertEqual(r["subset_accuracy"], 1)
            self.assertIn("sha256", r["provenance"]["inputs"]["thresholds"])
            self.cli("functional-groups", "--targets", "examples/validation.targets.jsonl", "--predictions", "examples/validation.scores.jsonl",
                     "--labels", "examples/labels.json", "--missing-labels", "reject", "--zero-division", "0", "--thresholds", path, expected=2)

    def test_misalignment_duplicate_and_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            a.write_text('{"id":"a"}\n')
            b.write_text('{"id":"b"}\n')
            with self.assertRaisesRegex(ValueError, "ID sets differ"):
                aligned(a, b)
            b.write_text('{"id":"b"}\n{"id":"b"}\n')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                records(b)
            b.write_text('{"id":"b","peaks":[NaN]}\n')
            with self.assertRaises(ValueError):
                records(b)

    def test_cli_failure_has_no_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            self.cli("functional-groups", "--targets", "examples/classification.targets.jsonl", "--predictions", "examples/structure.predictions.jsonl",
                     "--labels", "examples/labels.json", "--missing-labels", "reject", "--zero-division", "0", "--output", output, expected=2)
            self.assertFalse(output.exists())

    def test_export_preserves_order_peaks_and_label_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.pkl"
            path.write_bytes(pickle.dumps([dict(smiles="CCO", h_shift=[1, 1, 2], c_shift=[10], fg_onehot=np.array([1, 0], dtype=np.uint8))]))
            rows, _ = export(path, task="spectra", id_prefix="test", nucleus="1H")
            self.assertEqual(rows[0]["peaks"], [1, 1, 2])
            self.assertEqual(rows[0]["id"], "test:0")
            rows, _ = export(path, task="functional-groups", id_prefix="test", label_schema=ROOT / "examples/labels.json")
            self.assertEqual(rows[0]["labels"], [1, 0])
            with self.assertRaises(ValueError):
                export(path, task="functional-groups", id_prefix="test", label_schema=ROOT / "configs/labels-fg22.json")

    def test_export_rejects_arbitrary_globals(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "untrusted.pkl"
            path.write_bytes(pickle.dumps(Path("somewhere")))
            with self.assertRaisesRegex(ValueError, "Unsupported pickle global"):
                export(path, task="structure", id_prefix="test")


try:
    from rdkit import Chem
    HAVE_RDKIT = True
except ImportError:
    HAVE_RDKIT = False


@unittest.skipUnless(HAVE_RDKIT, "Install requirements-chem.txt for structure tests")
class StructureTests(unittest.TestCase):
    def test_rank_preservation_and_empty_candidate_list(self):
        y = [{"id": "a", "smiles": "CCO"}, {"id": "b", "smiles": "CCCC"}]
        p = [{"candidates": ["not-a-smiles", "CCO"]}, {"candidates": []}]
        r = evaluate_structure(y, p, ks=[1, 2], match="raw", invalid="zero")
        self.assertEqual(r["exact_match@1"], 0)
        self.assertEqual(r["exact_match@2"], 0.5)
        self.assertEqual(r["n_invalid_candidates_scored"], 1)

    def test_raw_and_canonical_are_distinct(self):
        y, p = [{"id": "a", "smiles": "CCO"}], [{"candidates": ["OCC"]}]
        self.assertEqual(evaluate_structure(y, p, ks=[1], match="raw", invalid="error")["exact_match@1"], 0)
        self.assertEqual(evaluate_structure(y, p, ks=[1], match="canonical-isomeric", invalid="error")["exact_match@1"], 1)

    def test_stereochemistry_is_explicit(self):
        y, p = [{"id": "a", "smiles": "C[C@H](O)F"}], [{"candidates": ["C[C@@H](O)F"]}]
        self.assertEqual(evaluate_structure(y, p, ks=[1], match="canonical-isomeric", invalid="error")["exact_match@1"], 0)
        self.assertEqual(evaluate_structure(y, p, ks=[1], match="canonical-nonisomeric", invalid="error")["exact_match@1"], 1)

    def test_fingerprints_and_tokens_cli(self):
        r = subprocess.run([sys.executable, "-m", "nmrgym_eval", "structure", "--targets", "examples/structure.targets.jsonl",
                            "--predictions", "examples/structure.predictions.jsonl", "--top-k", "1", "2", "--match", "raw", "--invalid", "zero",
                            "--fingerprint-config", "examples/fingerprints.json", "--zero-norm", "0", "--topk-reduction", "best", "--tokens"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["exact_match@1"], 0.5)
        self.assertEqual(result["exact_match@2"], 1)
        self.assertEqual(result["token_accuracy@2"], 1)
        for name in ("morgan", "torsion", "atom_pair"):
            self.assertAlmostEqual(result[f"{name}_tanimoto@2"], 1)
            self.assertAlmostEqual(result[f"{name}_cosine@2"], 1)


if __name__ == "__main__":
    unittest.main()
