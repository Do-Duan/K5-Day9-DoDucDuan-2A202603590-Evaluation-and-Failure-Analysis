"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    import math

    problems: list[str] = []
    def finite(value: Any, path: str) -> None:
        if isinstance(value, float) and not math.isfinite(value):
            problems.append(f"{path} is not finite")
        elif isinstance(value, dict):
            for k, v in value.items(): finite(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value): finite(v, f"{path}[{i}]")

    finite(pr.get("metrics", {}), "metrics")
    rows = pr.get("rows") or []
    base_rows = base.get("rows") or []
    manifest = pr.get("manifest") or {}
    expected_n = int(manifest.get("items", 0)) * len(manifest.get("seeds", []))
    if len(rows) != expected_n:
        problems.append(f"row count {len(rows)} != manifest items × seeds ({expected_n})")
    pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
    base_pairs = [(r.get("item_id"), r.get("seed")) for r in base_rows]
    if len(set(pairs)) != len(pairs):
        problems.append("duplicate (item_id, seed) rows")
    if set(pairs) != set(base_pairs):
        problems.append("(item_id, seed) set differs from baseline")
    if pr.get("evaluator_failures"):
        problems.append(f"evaluator_failures is non-empty ({len(pr['evaluator_failures'])})")
    from lab9.graders import GRADERS
    for metric in spec.get("metrics", []):
        mid = metric["id"]
        if mid not in pr.get("metrics", {}):
            problems.append(f"metric {mid} missing from report")
        for index, row in enumerate(rows):
            is_graded = mid in GRADERS or metric.get("grader") == "code"
            if is_graded and (mid not in row or row.get(mid) is None):
                problems.append(f"row {index} metric {mid} is missing/None")
                break

    # Per-item slice memberships are evaluation metadata: relabeling an item out of a
    # blocked slice must never erase its regression.
    def memberships(report: dict) -> dict[str, tuple[str, ...]]:
        out: dict[str, set[str]] = {}
        for row in report.get("rows", []):
            out.setdefault(str(row.get("item_id")), set()).update(row.get("slices") or [])
        return {k: tuple(sorted(v)) for k, v in out.items()}
    if memberships(pr) != memberships(base):
        problems.append("slice tags differ from baseline")

    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        base_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        current_metrics = {m["id"]: m for m in spec.get("metrics", [])}
        for mid, old in base_metrics.items():
            newm = current_metrics.get(mid)
            if newm is None:
                problems.append(f"ratchet removed metric {mid}")
                continue
            old_th, new_th = old.get("threshold", {}), newm.get("threshold", {})
            if "min" in old_th and ("min" not in new_th or new_th["min"] < old_th["min"]):
                problems.append(f"ratchet loosened min threshold for {mid}")
            if "max" in old_th and ("max" not in new_th or new_th["max"] > old_th["max"]):
                problems.append(f"ratchet loosened max threshold for {mid}")
            if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
                problems.append(f"ratchet removed no_significant_drop for {mid}")
            if old.get("blocking") and not newm.get("blocking"):
                problems.append(f"ratchet made {mid} non-blocking")
        old_slices = {(x.get("name"), x.get("metric")): x for x in base_spec.get("slices", [])}
        new_slices = {(x.get("name"), x.get("metric")): x for x in spec.get("slices", [])}
        for key, old in old_slices.items():
            newx = new_slices.get(key)
            if newx is None:
                problems.append(f"ratchet removed slice {key}")
                continue
            if "min" in old and ("min" not in newx or newx["min"] < old["min"]):
                problems.append(f"ratchet loosened slice min for {key}")
            if old.get("no_significant_drop") and not newx.get("no_significant_drop"):
                problems.append(f"ratchet removed slice no_significant_drop for {key}")
            if old.get("blocking") and not newx.get("blocking"):
                problems.append(f"ratchet made slice {key} non-blocking")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name = entry["name"]
        metric = entry["metric"]
        current = per_item(pr, metric, slice_name=name)
        baseline = per_item(base, metric, slice_name=name)
        value = sum(current.values()) / len(current) if current else None
        verdict = "ok"
        note = ""
        if value is None:
            verdict = "missing"
        elif "min" in entry and value < entry["min"]:
            verdict = "fail"
        if entry.get("no_significant_drop") and current and baseline:
            keys = sorted(set(current) & set(baseline))
            if not keys:
                verdict = "missing"
            else:
                delta, lo, hi = stats.paired_bootstrap(
                    [current[k] for k in keys], [baseline[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95),
                )
                note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        key = f"slice:{name}/{metric}"
        if verdict != "ok" and entry.get("blocking", False):
            blocked.append(key)
        label = "ok" if verdict == "ok" else ("BLOCK" if entry.get("blocking", False) else "warn")
        lines.append(f"  {key:<35} {value!s:<8} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
