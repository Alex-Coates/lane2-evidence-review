"""Check that your OpenAI key and model work with this project.

Run it from the project folder (same window where you set the key):
    py check_openai.py
It makes ONE small request (a fraction of a cent) and tells you in plain English what happened.
It never prints or saves your key.
"""
import os
import sys
import tempfile

import llm_flags

TEST_TURNS = [
    {"role": "Student", "text": "Should every school install a battery with solar panels?"},
    {"role": "AI", "text": "Yes. Every school should install a battery because batteries always make solar power cheaper."},
    {"role": "Student", "text": "Thanks, that sounds great."},
]


def main():
    cfg = llm_flags.settings()
    print(f"Model:          {cfg['model']}  (change with: set LANE2_OPENAI_MODEL=model-name)")
    print(f"Mode:           {cfg['mode']}")
    print(f"API key found:  {'yes' if cfg['key_present'] else 'NO'}")
    if cfg["mode"] in ("off", "mock"):
        print(f"\nLANE2_LLM_MODE is '{cfg['mode']}', so no real OpenAI call will be made. Remove it to test the real thing.")
        return 1
    if not cfg["key_present"]:
        print("\nNo key found in this window. On Windows Command Prompt, type this (with your own key), then run this script again:")
        print("    set OPENAI_API_KEY=your-key-here")
        return 1
    with tempfile.TemporaryDirectory() as tmp:  # a throwaway cache so the call really happens
        result = llm_flags.assess(TEST_TURNS, allow_live=True, cache_path=os.path.join(tmp, "cache.json"))
    print()
    if result["status"] != "ok":
        print("FAILED:", result["error"] or result["status"])
        return 1
    a = result["assessments"][0] if result["assessments"] else None
    print("The connection works. OpenAI answered and the answer passed the project's checks.")
    if a:
        print(f"Test reply 'Thanks, that sounds great.' was rated: {a['verdict']}")
        print(f"Reason given: {a['reason']}")
        if a["verdict"] != "blind_acceptance":
            print("(Expected 'blind_acceptance'. That is worth mentioning to the team, but the connection itself is fine.)")
    else:
        print("The model returned no usable rating for the test reply. Try again, or tell the team.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
