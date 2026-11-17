"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge labels must have the same length")
    h = [str(x).strip().upper() for x in human]
    j = [str(x).strip().upper() for x in judge]
    if any(x not in {"PASS", "FAIL"} for x in h + j):
        raise ValueError("labels must be PASS or FAIL")
    return {
        "tp": sum(a == "FAIL" and b == "FAIL" for a, b in zip(h, j)),
        "fp": sum(a == "PASS" and b == "FAIL" for a, b in zip(h, j)),
        "fn": sum(a == "FAIL" and b == "PASS" for a, b in zip(h, j)),
        "tn": sum(a == "PASS" and b == "PASS" for a, b in zip(h, j)),
    }


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    pden = cm["tp"] + cm["fp"]
    rden = cm["tp"] + cm["fn"]
    return (cm["tp"] / pden if pden else 0.0,
            cm["tp"] / rden if rden else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = sum(cm.values())
    if n == 0:
        raise ValueError("kappa undefined for empty labels")
    po = (cm["tp"] + cm["tn"]) / n
    human_fail = cm["tp"] + cm["fn"]
    human_pass = cm["fp"] + cm["tn"]
    judge_fail = cm["tp"] + cm["fp"]
    judge_pass = cm["fn"] + cm["tn"]
    pe = (human_fail * judge_fail + human_pass * judge_pass) / (n * n)
    if pe == 1:
        raise ValueError("kappa undefined when expected agreement is 1")
    return (po - pe) / (1 - pe)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if not all(0.0 <= x <= 1.0 for x in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be between 0 and 1")
    denom = sensitivity + specificity - 1.0
    if denom <= 0:
        raise ValueError("sensitivity and specificity do not identify prevalence")
    return min(1.0, max(0.0, (observed_rate + specificity - 1.0) / denom))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np

    if len(a) != len(b):
        raise ValueError("a and b must have the same length")
    if not a:
        raise ValueError("paired bootstrap requires non-empty samples")
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    differences = a_arr - b_arr
    mean_difference = float(np.mean(differences))
    if np.all(differences == 0):
        return (0.0, 0.0, 0.0)

    generator = np.random.default_rng(rng)
    # Resample paired item differences; this is equivalent to applying the
    # same bootstrap indices to both samples and is cheaper than two means.
    indices = generator.integers(0, len(differences), size=(len(differences), n_resamples))
    bootstrap_means = np.mean(differences[indices], axis=0)
    alpha = (1.0 - confidence) / 2.0
    lo, hi = np.quantile(bootstrap_means, [alpha, 1.0 - alpha])
    return mean_difference, float(lo), float(hi)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_k_args(n, c, k)
    # Avoid computing a combination for the certain-success boundary.
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_k_args(n, c, k)
    if c < k:
        return 0.0
    return comb(c, k) / comb(n, k)


def _validate_pass_k_args(n: int, c: int, k: int) -> None:
    if (not isinstance(n, int) or isinstance(n, bool)
            or not isinstance(c, int) or isinstance(c, bool)
            or not isinstance(k, int) or isinstance(k, bool)
            or n < 0 or c < 0 or c > n or k <= 0 or k > n):
        raise ValueError("require integers with 0 <= c <= n and 1 <= k <= n")
