"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def _is_non_finite(val: object) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and not math.isfinite(float(val))


def _ratchet_problems(spec: dict, base_spec: dict) -> list[str]:
    """Ensure thresholds and slices never get looser on the same eval-set version."""
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []
    problems: list[str] = []
    bm_by_id = {m["id"]: m for m in (base_spec.get("metrics") or [])}
    pm_by_id = {m["id"]: m for m in (spec.get("metrics") or [])}
    for mid, bm in bm_by_id.items():
        if mid not in pm_by_id:
            problems.append(f"ratchet: metric {mid} removed")
            continue
        pm = pm_by_id[mid]
        if bm.get("blocking") and not pm.get("blocking"):
            problems.append(f"ratchet: metric {mid} became non-blocking")
        bth, pth = bm.get("threshold") or {}, pm.get("threshold") or {}
        if "max" in bth and ("max" not in pth or pth["max"] > bth["max"]):
            problems.append(f"ratchet: metric {mid} max rose ({bth['max']} -> {pth.get('max')})")
        if "max_increase" in bth and ("max_increase" not in pth or pth["max_increase"] > bth["max_increase"]):
            problems.append(
                f"ratchet: metric {mid} max_increase rose ({bth['max_increase']} -> {pth.get('max_increase')})"
            )
        if "min" in bth and ("min" not in pth or pth["min"] < bth["min"]):
            problems.append(f"ratchet: metric {mid} min fell ({bth['min']} -> {pth.get('min')})")
        if bth.get("no_significant_drop") and not pth.get("no_significant_drop"):
            problems.append(f"ratchet: metric {mid} dropped no_significant_drop")

    bs_by_key = {(s["name"], s["metric"]): s for s in (base_spec.get("slices") or [])}
    ps_by_key = {(s["name"], s["metric"]): s for s in (spec.get("slices") or [])}
    for (name, metric), bs in bs_by_key.items():
        if (name, metric) not in ps_by_key:
            problems.append(f"ratchet: slice {name}/{metric} removed")
            continue
        ps = ps_by_key[(name, metric)]
        if bs.get("blocking") and not ps.get("blocking"):
            problems.append(f"ratchet: slice {name}/{metric} became non-blocking")
        if bs.get("min") is not None and (ps.get("min") is None or ps["min"] < bs["min"]):
            problems.append(f"ratchet: slice {name}/{metric} min fell ({bs['min']} -> {ps.get('min')})")
        if bs.get("max") is not None and (ps.get("max") is None or ps["max"] > bs["max"]):
            problems.append(f"ratchet: slice {name}/{metric} max rose ({bs['max']} -> {ps.get('max')})")
        if bs.get("no_significant_drop") and not ps.get("no_significant_drop"):
            problems.append(f"ratchet: slice {name}/{metric} dropped no_significant_drop")
    return problems


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
    problems: list[str] = []
    for mid, val in (pr.get("metrics") or {}).items():
        if _is_non_finite(val):
            problems.append(f"non-finite metric {mid}={val!r}")
    if pr.get("evaluator_failures"):
        problems.append(f"evaluator_failures non-empty ({len(pr['evaluator_failures'])})")

    pr_manifest = pr.get("manifest") or {}
    pr_rows = pr.get("rows") or []
    base_rows = base.get("rows") or []
    pr_items = pr_manifest.get("items")
    pr_seeds = list(pr_manifest.get("seeds") or [])
    if pr_items is None or len(pr_rows) != int(pr_items) * len(pr_seeds):
        problems.append(f"row count {len(pr_rows)} != manifest {pr_items} x {len(pr_seeds)}")
    if len(pr_seeds) != len(set(pr_seeds)):
        problems.append("duplicate seed in manifest.seeds")

    pr_keys = [(r.get("item_id"), r.get("seed")) for r in pr_rows]
    if len(pr_keys) != len(set(pr_keys)):
        problems.append("duplicate (item_id, seed) row(s) in pr")
    base_keys = {(r.get("item_id"), r.get("seed")) for r in base_rows}
    if set(pr_keys) != base_keys:
        problems.append("(item_id, seed) set differs from baseline")

    spec_metric_ids = {m["id"] for m in (spec.get("metrics") or [])}
    row_keys = {k for r in (*pr_rows, *base_rows) for k in r}
    graded_ids = sorted(spec_metric_ids & row_keys)
    for r in pr_rows:
        bad_cols = [
            mid for mid in graded_ids
            if r.get(mid) is None or _is_non_finite(r.get(mid))
        ]
        if bad_cols:
            problems.append(f"row {r.get('item_id')}@{r.get('seed')} has missing/non-finite {bad_cols}")
            break

    base_slices = {(r.get("item_id"), r.get("seed")): sorted(r.get("slices") or []) for r in base_rows}
    for r in pr_rows:
        key = (r.get("item_id"), r.get("seed"))
        if key in base_slices and sorted(r.get("slices") or []) != base_slices[key]:
            problems.append(f"slice tags differ from baseline on {key[0]}@{key[1]}")
            break

    if base_spec is not None:
        problems.extend(_ratchet_problems(spec, base_spec))
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
    for s in spec.get("slices") or []:
        name, metric = s["name"], s["metric"]
        sid = f"slice:{name}/{metric}"
        a = per_item(pr, metric, slice_name=name)
        val = sum(a.values()) / len(a) if a else None
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif s.get("min") is not None and val < s["min"]:
            verdict = "fail"
        if s.get("no_significant_drop") and val is not None:
            b = per_item(base, metric, slice_name=name)
            keys = sorted(set(a) & set(b))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [a[k] for k in keys],
                    [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
            elif b:
                verdict = "fail"
                note = "no paired items"
        if verdict != "ok" and s.get("blocking"):
            blocked.append(sid)
        th = {k: s[k] for k in ("min", "no_significant_drop") if s.get(k) is not None}
        val_str = f"{val:.4f}" if val is not None else "None"
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if s.get("blocking") else "warn")
        lines.append(f"  {sid:<32} {val_str:<8} {json.dumps(th):<38} {note:<28} {label}")
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