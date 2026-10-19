"""Compare a simple phrase-list baseline with the OpenAI critique check on the labelled replies.

The phrase list is NOT used by the application. It stands in for "what a simple fixed rule would catch",
so the report can show how much the model adds.

Run from the project folder (after check_openai.py works):
    py eval/evaluate_flags.py
It makes one small request per item (36 in total, well under a dollar), saves the answers in
eval/eval_cache.json so a second run is free, and writes eval/results.md for the report.
"Needs a closer look" means the reply is generic or blind acceptance.
"""
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import llm_flags  # noqa: E402
from labelled_replies import ITEMS  # noqa: E402

CACHE = os.path.join(HERE, "eval_cache.json")
NAMES = {"S": "substantive", "G": "generic", "B": "blind_acceptance"}


# A simple fixed phrase list, for comparison only (not part of the application).
BASELINE_PHRASES = ("good answer", "looks correct", "this looks correct", "thanks", "thank you", "i agree")


def rule_verdict(ai, reply):
    normalised = " ".join(re.findall(r"[a-z0-9]+", reply.lower()))
    return "needs_look" if normalised in BASELINE_PHRASES else "ok"


def llm_verdict(ai, reply):
    turns = [{"role": "Student", "text": "Please help with my question."}, {"role": "AI", "text": ai},
             {"role": "Student", "text": reply}]
    result = llm_flags.assess(turns, allow_live=True, cache_path=CACHE)
    if result["status"] != "ok" or not result["assessments"]:
        return None, result
    return result["assessments"][0]["verdict"], result


def metrics(rows, key):
    tp = sum(1 for r in rows if r["truth_flag"] and r[key])
    fp = sum(1 for r in rows if not r["truth_flag"] and r[key])
    fn = sum(1 for r in rows if r["truth_flag"] and not r[key])
    tn = sum(1 for r in rows if not r["truth_flag"] and not r[key])
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1,
            "accuracy": (tp + tn) / len(rows)}


def main():
    cfg = llm_flags.settings()
    mode = cfg["mode"]
    if mode != "mock" and not cfg["key_present"] and not os.path.exists(CACHE):
        print("No OpenAI key is set and there are no saved results. Set OPENAI_API_KEY (see README), or use")
        print("LANE2_LLM_MODE=mock for a dry run that proves the script works (its numbers mean nothing).")
        return 1
    rows, errors, mode_seen = [], 0, set()
    for ai, reply, label, note in ITEMS:
        verdict, result = llm_verdict(ai, reply)
        mode_seen.add(result["mode"])
        if verdict is None:
            errors += 1
            print(f"Could not rate: {reply[:40]!r} -> {result['error'] or result['status']}")
        rows.append({"reply": reply, "label": label, "note": note, "truth_flag": label in ("G", "B"),
                     "rules_flag": rule_verdict(ai, reply) == "needs_look",
                     "llm_verdict": verdict, "llm_flag": verdict in llm_flags.FLAG_VERDICTS})
    m_rules, m_llm = metrics(rows, "rules_flag"), metrics(rows, "llm_flag")
    rated = [r for r in rows if r["llm_verdict"]]
    three_way = sum(1 for r in rated if r["llm_verdict"] == NAMES[r["label"]]) / len(rated) if rated else 0.0
    simulated = "mock" in mode_seen

    lines = ["# Phrase-list baseline vs OpenAI critique check: results", ""]
    if simulated:
        lines += ["**SIMULATED RUN: the critique check used the word-pattern stand-in, not a real model. These numbers are not valid evidence.**", ""]
    lines += [f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M')} · Model: {cfg['model']} · Rubric v{llm_flags.RUBRIC_VERSION} · "
              f"{len(rows)} labelled replies (draft labels, to be confirmed by the team) · Replies the model could not rate: {errors}", "",
              "Positive = the reply needs a closer look (generic or blind acceptance).", "",
              "| Method | Correctly flagged | Wrongly flagged | Missed | Correctly not flagged | Precision | Recall | F1 | Accuracy |",
              "|---|---|---|---|---|---|---|---|---|"]
    for name, m in (("Simple phrase-list baseline", m_rules), ("OpenAI critique check", m_llm)):
        lines.append(f"| {name} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} | {m['accuracy']:.2f} |")
    lines += ["", f"Three-way agreement of the critique check with the labels (substantive / generic / blind acceptance): {three_way:.0%} of {len(rated)} rated replies.", "",
              "## Replies where a method disagreed with the label (read these before trusting the numbers)", "",
              "| Reply | Label | Baseline | Critique check | Note |", "|---|---|---|---|---|"]
    for r in rows:
        if r["rules_flag"] != r["truth_flag"] or r["llm_flag"] != r["truth_flag"] or r["llm_verdict"] is None:
            lines.append(f"| {r['reply'][:70]} | {NAMES[r['label']]} | {'flag' if r['rules_flag'] else 'no flag'} | {r['llm_verdict'] or 'not rated'} | {r['note']} |")
    out = "\n".join(lines) + "\n"
    with open(os.path.join(HERE, "results.md"), "w", encoding="utf-8") as f:
        f.write(out)
    print(out)
    print("Saved to eval/results.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
