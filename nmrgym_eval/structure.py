"""Structure scoring; candidate ranks are preserved, including invalid entries."""

from functools import lru_cache

import numpy as np

from .metrics import fingerprint_similarity, token_accuracy


def chemistry():
    try:
        from rdkit import Chem
        from rdkit.Chem import rdFingerprintGenerator
    except ImportError as exc:
        raise ValueError("Install requirements-chem.txt for RDKit structure evaluation") from exc
    return Chem, rdFingerprintGenerator


def generators(config):
    _, g = chemistry()
    # Require every supported setting rather than silently taking RDKit defaults.
    fields = {
        "morgan": {"radius", "countSimulation", "includeChirality", "useBondTypes", "onlyNonzeroInvariants", "includeRingMembership", "countBounds", "includeRedundantEnvironments"},
        "torsion": {"includeChirality", "torsionAtomCount", "countSimulation", "countBounds"},
        "atom_pair": {"minDistance", "maxDistance", "includeChirality", "use2D", "countSimulation", "countBounds"},
    }
    constructors = {"morgan": g.GetMorganGenerator, "torsion": g.GetTopologicalTorsionGenerator, "atom_pair": g.GetAtomPairGenerator}
    if not isinstance(config, dict) or not config or set(config) - fields.keys():
        raise ValueError("Fingerprint config must select morgan, torsion, and/or atom_pair")
    result = {}
    for name, params in config.items():
        if not isinstance(params, dict) or set(params) != fields[name]:
            raise ValueError(f"{name} requires exactly these settings: {sorted(fields[name])}")
        result[name] = constructors[name](fpSize=2048, **params)
    return result


def evaluate_structure(targets, predictions, *, ks, match, invalid, fingerprint_config=None,
                       topk_reduction=None, zero_norm=None, score_tokens=False):
    if not targets or len(targets) != len(predictions):
        raise ValueError("Expected nonempty, aligned target and prediction lists")
    if not ks or any(k < 1 for k in ks):
        raise ValueError("top-k values must be positive")
    if invalid not in ("error", "zero"):
        raise ValueError("invalid must be error or zero")
    if match not in ("raw", "canonical-isomeric", "canonical-nonisomeric"):
        raise ValueError("Unknown SMILES matching policy")
    if (fingerprint_config or score_tokens) and topk_reduction not in ("best", "mean"):
        raise ValueError("Token/fingerprint scoring requires --topk-reduction best or mean")
    gens = generators(fingerprint_config) if fingerprint_config else {}
    if gens and zero_norm is None:
        raise ValueError("Fingerprint scoring requires --zero-norm")
    chem = chemistry()[0]

    @lru_cache(maxsize=65536)
    def parse(smi):
        return chem.MolFromSmiles(smi) if smi.strip() else None

    def canonical(smi, mol):
        return smi if match == "raw" else chem.MolToSmiles(mol, canonical=True, isomericSmiles=match == "canonical-isomeric")

    sums = {f"exact_match@{k}": 0.0 for k in ks}
    for k in ks:
        if score_tokens:
            sums[f"token_accuracy@{k}"] = 0.0
        for name in gens:
            for metric in ("tanimoto", "cosine"):
                sums[f"{name}_{metric}@{k}"] = 0.0
    invalid_count, empty_count = 0, 0
    for target, predicted in zip(targets, predictions):
        truth, candidates = target["smiles"], predicted["candidates"]
        if not isinstance(truth, str) or not truth.strip() or not isinstance(candidates, list) or any(not isinstance(s, str) for s in candidates):
            raise ValueError("smiles must be nonempty strings; candidates must be ranked lists of strings")
        if score_tokens and (not isinstance(predicted.get("candidate_tokens"), list) or len(predicted["candidate_tokens"]) != len(candidates)):
            raise ValueError("candidate_tokens must align one-to-one with candidates")
        empty_count += not candidates
        mol = parse(truth) if chem else None
        if chem and (mol is None or mol.GetNumAtoms() == 0):
            raise ValueError(f"Invalid target SMILES for {target['id']}")
        ref = canonical(truth, mol)
        truth_fp = {name: np.asarray(gen.GetFingerprintAsNumPy(mol), dtype=float) for name, gen in gens.items()}
        exact, token, fp = [], [], {name: {metric: [] for metric in ("tanimoto", "cosine")} for name in gens}
        for j, smi in enumerate(candidates[:max(ks)]):
            candidate = parse(smi) if chem else None
            valid = bool(smi.strip()) and (not chem or (candidate is not None and candidate.GetNumAtoms() > 0))
            invalid_count += not valid
            if not valid and invalid == "error":
                raise ValueError(f"Invalid candidate at {target['id']} rank {j + 1}")
            exact.append(float(valid and canonical(smi, candidate) == ref))
            if score_tokens:
                value = token_accuracy(target["tokens"], predicted["candidate_tokens"][j])
                token.append(value if valid else 0.0)
            for name, gen in gens.items():
                bits = np.asarray(gen.GetFingerprintAsNumPy(candidate), dtype=float) if valid else None
                for metric in fp[name]:
                    fp[name][metric].append(fingerprint_similarity(truth_fp[name], bits, metric, zero_norm=zero_norm) if valid else 0.0)
        for k in ks:
            sums[f"exact_match@{k}"] += float(any(exact[:k]))
            # Missing ranks contribute zero when taking the mean; ranks never shift.
            def reduce(values):
                return max(values[:k], default=0.0) if topk_reduction == "best" else sum(values[:k]) / k
            if score_tokens:
                sums[f"token_accuracy@{k}"] += reduce(token)
            for name in gens:
                for metric in fp[name]:
                    sums[f"{name}_{metric}@{k}"] += reduce(fp[name][metric])
    return {"n_samples": len(targets), "n_invalid_candidates_scored": invalid_count,
            "n_empty_candidate_lists": int(empty_count),
            **{key: value / len(targets) for key, value in sums.items()}}
