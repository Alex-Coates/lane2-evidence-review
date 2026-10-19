"""Run the OpenAI critique check on every submission that does not have a result yet.

Use this after setting your key (see README). It also fills llm_cache.json, so the fictional
submissions show their results for anyone who runs the project later, without needing a key.
    py run_critique_checks.py
Decisions you have already saved on flags that still exist are kept.
"""
import sys

import app as lane2
import llm_flags


def main():
    cfg = llm_flags.settings()
    if cfg["mode"] in ("off", "mock") or not cfg["key_present"]:
        print("No live OpenAI check is possible: set OPENAI_API_KEY first (and do not set LANE2_LLM_MODE to off or mock).")
        print("Run check_openai.py to test your key.")
        return 1
    done = skipped = failed = 0
    with lane2.app.app_context():
        db = lane2.get_db()
        for row in db.execute("SELECT * FROM submissions ORDER BY id").fetchall():
            run = lane2.latest_llm_run(db, row["id"])
            if run is not None and run["status"] == "ok" and run["mode"] in ("live", "cached"):
                skipped += 1
                continue
            turns = lane2.load_turns(db, row["id"])
            assessment = llm_flags.assess(turns, allow_live=True, usage_ok=lane2.live_calls_ok(db))
            if assessment["status"] == "ok":
                lane2.save_llm_run(db, row["id"], assessment)
                lane2.rebuild_keeping_decisions(db, row["id"], row["final_text"], turns)
                db.commit()
                n = sum(1 for a in assessment["assessments"] if a["verdict"] in llm_flags.FLAG_VERDICTS)
                print(f"{row['ref']}: {assessment['mode']}, {len(assessment['assessments'])} replies rated, {n} flagged")
                done += 1
            elif assessment["status"] == "not_applicable":
                skipped += 1
            else:
                print(f"{row['ref']}: {assessment['status']} - {assessment['error']}")
                failed += 1
    print(f"\nDone: {done} checked, {skipped} skipped (already checked or nothing to rate), {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
