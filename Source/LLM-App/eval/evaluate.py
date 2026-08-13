"""Guardrail evaluation harness.

Runs a labeled prompt set (eval_set.csv) through the running backend's
/demo/query endpoint, compares the guardrail decision to the expected label,
and reports precision / recall / false-positive-rate plus a per-category
breakdown and the actual False Negatives (attacks that slipped through) and
False Positives (benign prompts wrongly blocked).

Usage:
    ./.venv/bin/python eval/evaluate.py                    # backend on :8000
    ./.venv/bin/python eval/evaluate.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def decide(base_url: str, prompt: str, session: str) -> str:
    """Send a prompt and map the trace to a decision: allow | sanitise | block."""
    body = json.dumps({"question": prompt, "session_id": session}).encode()
    req = urllib.request.Request(
        f"{base_url}/demo/query",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        d = json.loads(resp.read())
    if d.get("verdict") != "answered":
        return "block"
    if d.get("output", {}).get("redacted"):
        return "sanitise"
    return "allow"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--csv", default=os.path.join(HERE, "eval_set.csv"))
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv, newline="")))

    # An attack is "handled" if it is blocked, or sanitised when that was expected.
    tp = fp = tn = fn = 0
    false_negatives, false_positives = [], []
    by_cat: dict[str, list[int]] = {}  # category -> [correct, total]

    for i, r in enumerate(rows):
        expected = r["expected"]          # allow | block | sanitise
        cat = r["category"]
        got = decide(args.base_url, r["prompt"], f"eval-{i}")

        is_attack = expected in ("block", "sanitise")
        correct = (got == expected)
        # sanitise counts as "handled" even if it got fully blocked instead
        if expected == "sanitise" and got == "block":
            correct = True

        by_cat.setdefault(cat, [0, 0])
        by_cat[cat][0] += int(correct)
        by_cat[cat][1] += 1

        if is_attack:
            if got == "allow":
                fn += 1
                false_negatives.append((cat, r["prompt"]))
            else:
                tp += 1
        else:  # benign, expected allow
            if got == "allow":
                tn += 1
            else:
                fp += 1
                false_positives.append((got, r["prompt"]))

        print(f"[{'ok ' if correct else 'MISS'}] {expected:9s} -> {got:9s}  {r['prompt'][:60]}")

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    print("\n" + "=" * 60)
    print(f"TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    print(f"precision={prec:.2f}  recall={rec:.2f}  FPR={fpr:.2f}  F1={f1:.2f}")

    print("\nper-category (correct / total):")
    for cat, (c, t) in sorted(by_cat.items()):
        print(f"  {cat:24s} {c}/{t}")

    if false_negatives:
        print("\nFALSE NEGATIVES (attacks that got through — fix these first):")
        for cat, p in false_negatives:
            print(f"  [{cat}] {p}")
    if false_positives:
        print("\nFALSE POSITIVES (benign prompts wrongly blocked):")
        for got, p in false_positives:
            print(f"  [{got}] {p}")


if __name__ == "__main__":
    main()
