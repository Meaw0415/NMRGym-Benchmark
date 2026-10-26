import math
import unittest

import numpy as np

from nmrgym_eval.metrics import (apply_thresholds, cosine_similarity, fingerprint_similarity,
                                fit_thresholds, gaussian_vector, multilabel_metrics,
                                set_similarity, token_accuracy)


class MetricTests(unittest.TestCase):
    def test_classification_hand_calculation(self):
        r = multilabel_metrics([[1, 0], [0, 1]], [[1, 1], [0, 0]], missing="reject", zero_division=0)
        self.assertEqual(r["macro_accuracy"], 0.5)
        self.assertEqual(r["micro_accuracy"], 0.5)
        self.assertEqual(r["macro_recall"], 0.5)
        self.assertEqual(r["micro_recall"], 0.5)
        self.assertEqual(r["macro_f1"], 0.5)
        self.assertEqual(r["micro_f1"], 0.5)
        self.assertEqual(r["subset_accuracy"], 0)

    def test_missing_labels_are_not_negative(self):
        r = multilabel_metrics([[1, None], [0, 1]], [[1, 1], [0, 0]], missing="mask", zero_division=0)
        self.assertAlmostEqual(r["macro_accuracy"], 0.5)
        self.assertAlmostEqual(r["micro_accuracy"], 2 / 3)
        self.assertEqual(r["n_complete_samples"], 1)
        self.assertEqual(r["subset_accuracy"], 0)
        self.assertEqual(r["per_label"][1]["fp"], 0)

    def test_no_complete_subset_is_null(self):
        r = multilabel_metrics([[1, None], [None, 1]], [[1, 1], [1, 1]], missing="mask", zero_division=0)
        self.assertIsNone(r["subset_accuracy"])

    def test_classification_invalid_values(self):
        for y in ([[1, None]], [[1, -1]], [[1, float("inf")]], []):
            with self.subTest(y=y), self.assertRaises(ValueError):
                multilabel_metrics(y, [[1, 0]], missing="reject", zero_division=0)

    def test_zero_division_is_explicit(self):
        for zero in (0, 1):
            r = multilabel_metrics([[0]], [[0]], missing="reject", zero_division=zero)
            self.assertEqual(r["macro_f1"], zero)
            self.assertEqual(r["macro_recall"], zero)
            self.assertEqual(r["subset_accuracy"], 1)

    def test_thresholds_maximize_validation_f1(self):
        y, p = [[1], [0], [1]], [[0.8], [0.2], [0.6]]
        for comparison in ("ge", "gt"):
            t = fit_thresholds(y, p, missing="reject", zero_division=0, comparison=comparison, tie_break="highest")
            np.testing.assert_equal(apply_thresholds(p, t, comparison), y)

    def test_threshold_search_matches_exhaustive_decisions(self):
        rng = np.random.default_rng(42)
        for comparison in ("ge", "gt"):
            for tie in ("highest", "lowest"):
                for _ in range(12):
                    y = rng.integers(0, 2, (10, 1))
                    p = rng.integers(0, 5, (10, 1)) / 4
                    t = fit_thresholds(y, p, missing="reject", zero_division=0, comparison=comparison, tie_break=tie)
                    actual = multilabel_metrics(y, apply_thresholds(p, t, comparison), missing="reject", zero_division=0)["macro_f1"]
                    possible = [multilabel_metrics(y, apply_thresholds(p, [x], comparison), missing="reject", zero_division=0)["macro_f1"] for x in [-0.1, 0, 0.25, 0.5, 0.75, 1, 1.1]]
                    self.assertAlmostEqual(actual, max(possible))

    def test_threshold_ties_and_all_negative(self):
        a = fit_thresholds([[0], [0]], [[0.2], [0.8]], missing="reject", zero_division=0, comparison="ge", tie_break="highest")
        b = fit_thresholds([[0], [0]], [[0.2], [0.8]], missing="reject", zero_division=0, comparison="ge", tie_break="lowest")
        self.assertGreater(a[0], 0.8)
        self.assertEqual(b, [0.2])
        np.testing.assert_equal(apply_thresholds([[0.2], [0.8]], a, "ge"), [[0], [0]])

    def test_probability_validation(self):
        for p in ([[float("nan")]], [[1.2]], [[-0.1]], [[None]]):
            with self.assertRaises(ValueError):
                apply_thresholds(p, [0.5], "ge")

    def test_set_similarity_permutation_and_exponential(self):
        self.assertEqual(set_similarity([1, 2], [2, 1], 1), 1)
        self.assertAlmostEqual(set_similarity([1, 2], [3, 2], 1), math.exp(-1))
        self.assertAlmostEqual(set_similarity([10, 20], [30, 20], 10), math.exp(-1))

    def test_repeated_peaks_are_retained(self):
        self.assertAlmostEqual(set_similarity([1, 1, 2], [1, 2, 2], 1), math.exp(-1 / 3))
        np.testing.assert_allclose(gaussian_vector([1, 1], [0, 1, 2], 0.3), 2 * gaussian_vector([1], [0, 1, 2], 0.3))

    def test_unequal_or_empty_peaks_are_rejected(self):
        for a, b in [([1, 2], [1]), ([], []), ([1], [float("nan")])]:
            with self.assertRaises(ValueError):
                set_similarity(a, b, 1)

    def test_vector_similarity_and_zero_norm(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 1], zero_norm="error"), 1 / math.sqrt(2))
        self.assertEqual(cosine_similarity([0], [0], zero_norm=0), 0)
        with self.assertRaises(ValueError):
            cosine_similarity([0], [0], zero_norm="error")
        with self.assertRaises(ValueError):
            gaussian_vector([1], [2, 1], 1)

    def test_fingerprint_formulas(self):
        a, b = np.zeros(2048), np.zeros(2048)
        a[[1, 2]], b[[2, 3]] = 1, 1
        self.assertAlmostEqual(fingerprint_similarity(a, b, "tanimoto", zero_norm="error"), 1 / 3)
        self.assertAlmostEqual(fingerprint_similarity(a, b, "cosine", zero_norm="error"), 0.5)

    def test_token_denominator_and_positions(self):
        self.assertEqual(token_accuracy(["Cl", "C", "O"], ["Cl", "O"]), 1 / 3)
        self.assertEqual(token_accuracy([1, 2], [1, 2, 3]), 1)


if __name__ == "__main__":
    unittest.main()
