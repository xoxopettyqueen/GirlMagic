"""
Benford energy engine — SheGotGame / Girl Magic
Call from odds, props, lock, results, or any numeric list.
No UI. JSON-ready dict.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable, Mapping

# P(d) = log10(1 + 1/d)
BENFORD_EXPECTED = {d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)}

# Nigrini MAD bands (first digit)
MAD_CLOSE = 0.006
MAD_ACCEPTABLE = 0.012
MAD_MARGINALLY = 0.015
MIN_N = 25


def first_significant_digit(value: Any) -> int | None:
    """Leading digit 1–9. Skips 0, None, non-numeric."""
    try:
        x = abs(float(value))
    except (TypeError, ValueError):
        return None
    if x == 0 or math.isnan(x) or math.isinf(x):
        return None
    # scientific form avoids float noise on huge/tiny values
    exp = math.floor(math.log10(x))
    coeff = x / (10 ** exp)
    d = int(coeff)
    if d == 10:
        d = 1
    return d if 1 <= d <= 9 else None


def _freq(digits: list[int]) -> dict[int, float]:
    n = len(digits) or 1
    c = Counter(digits)
    return {d: c.get(d, 0) / n for d in range(1, 10)}


def _counts(digits: list[int]) -> dict[int, int]:
    c = Counter(digits)
    return {d: int(c.get(d, 0)) for d in range(1, 10)}


def _cosine(a: Mapping[int, float], b: Mapping[int, float]) -> float:
    num = sum(a[d] * b[d] for d in range(1, 10))
    na = math.sqrt(sum(a[d] ** 2 for d in range(1, 10)))
    nb = math.sqrt(sum(b[d] ** 2 for d in range(1, 10)))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, num / (na * nb)))


def _mad(actual: Mapping[int, float], expected: Mapping[int, float]) -> float:
    return sum(abs(actual[d] - expected[d]) for d in range(1, 10)) / 9.0


def _chi2(counts: Mapping[int, int], n: int, expected: Mapping[int, float]) -> float:
    s = 0.0
    for d in range(1, 10):
        exp = expected[d] * n
        if exp <= 0:
            continue
        s += (counts[d] - exp) ** 2 / exp
    return s


def benford_score_from_mad(mad: float) -> float:
    """1 = perfectly Benford, 0 = far off. Soft-cap at MAD 0.03."""
    return max(0.0, min(1.0, 1.0 - (mad / 0.03)))


def alignment_from_mad(mad: float, n: int) -> tuple[bool, str, str]:
    if n < MIN_N:
        return False, "Too Thin", "Need more numbers before the energy means anything."
    if mad <= MAD_CLOSE:
        return True, "Natural Energy (Benford-Aligned)", "close conformity"
    if mad <= MAD_ACCEPTABLE:
        return True, "Natural Energy (Benford-Aligned)", "acceptable conformity"
    if mad <= MAD_MARGINALLY:
        return False, "Mixed Energy (Marginal)", "marginally non-Benford"
    return False, "Artificial Energy (Non-Benford)", "nonconforming — capped / clustered / forced"


def analyze_benford(values: Iterable[Any], label: str = "") -> dict[str, Any]:
    """
    Input: any iterable of numbers (odds, props, payouts, stats).
    Output: JSON-serializable dict.
    """
    digits: list[int] = []
    skipped = 0
    for v in values or []:
        d = first_significant_digit(v)
        if d is None:
            skipped += 1
        else:
            digits.append(d)
    n = len(digits)
    actual = _freq(digits) if n else {d: 0.0 for d in range(1, 10)}
    counts = _counts(digits)
    expected = dict(BENFORD_EXPECTED)
    mad = _mad(actual, expected) if n else 1.0
    cosine = _cosine(actual, expected) if n else 0.0
    chi2 = _chi2(counts, n, expected) if n else None
    score = round(benford_score_from_mad(mad) * 0.7 + cosine * 0.3, 4) if n else 0.0
    aligned, tag, note = alignment_from_mad(mad, n)
    delta = {d: round(actual[d] - expected[d], 4) for d in range(1, 10)}
    return {
        "label": label or "dataset",
        "n": n,
        "skipped": skipped,
        "min_n": MIN_N,
        "actual_distribution": {str(d): round(actual[d], 4) for d in range(1, 10)},
        "expected_distribution": {str(d): round(expected[d], 4) for d in range(1, 10)},
        "counts": {str(d): counts[d] for d in range(1, 10)},
        "delta": {str(d): delta[d] for d in range(1, 10)},
        "mad": round(mad, 5),
        "cosine": round(cosine, 4),
        "chi_square": None if chi2 is None else round(chi2, 3),
        "benford_score": score,
        "alignment_flag": aligned,
        "alignment_label": tag,
        "alignment_note": note,
        "vibe": tag,
    }


def analyze_many(datasets: Mapping[str, Iterable[Any]]) -> dict[str, Any]:
    """Run Benford on several named lists. Returns {name: result, ...} plus ranking."""
    out = {}
    for name, vals in (datasets or {}).items():
        out[name] = analyze_benford(vals, label=name)
    ranked = sorted(out.values(), key=lambda r: r["benford_score"], reverse=True)
    return {
        "sets": out,
        "most_natural": ranked[0]["label"] if ranked else None,
        "most_artificial": ranked[-1]["label"] if ranked else None,
    }


if __name__ == "__main__":
    import json

    demo = [650, 550, 700, 800, 450, 600, 1200, 525, 475, 900, 575, 1000, 710]
    print(json.dumps(analyze_benford(demo, "demo_odds"), indent=2))
    
