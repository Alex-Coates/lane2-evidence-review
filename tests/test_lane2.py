"""Automated checks for Lane 2 Evidence Review (version 2).

Run from the project folder with:   python -m unittest discover -s tests -v

These tests supplement the team's manual functional test table. Each test uses
its own temporary database, so running them never changes instance/lane2.db.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# These tests must never call OpenAI or touch the real results cache, whatever is set on this computer.
# "mock" uses a simple word-pattern stand-in for the critique check, so critique flags can be tested offline.
_SAVED_ENV = {}


def setUpModule():
    """Set the stand-in mode only while this file's tests run (other test files set their own)."""
    for name in ("LANE2_LLM_MODE", "OPENAI_API_KEY"):
        _SAVED_ENV[name] = os.environ.get(name)
    os.environ["LANE2_LLM_MODE"] = "mock"
    os.environ.pop("OPENAI_API_KEY", None)


def tearDownModule():
    for name, value in _SAVED_ENV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value

import analysis  # noqa: E402
from app import create_app  # noqa: E402

TRANSCRIPT = "Student: Explain solar panels.\nAI: Solar panels turn sunlight into electricity for homes.\nStudent: Thanks."
FINAL = "Solar panels turn sunlight into electricity for homes."


class AnalysisTests(unittest.TestCase):
    def test_identical_text_scores_one(self):
        t = "solar panels turn sunlight into electricity for homes"
        self.assertEqual(analysis.similarity(t, t), 1.0)

    def test_text_under_five_words_scores_zero(self):
        self.assertEqual(analysis.similarity("Access improves wellbeing.", "Access improves wellbeing."), 0.0)

    def test_punctuation_and_case_ignored(self):
        self.assertEqual(analysis.similarity("ONE, two; three. four! FIVE?", "one two three four five"), 1.0)

    def test_parse_transcript_valid(self):
        turns = analysis.parse_transcript("Student: Hi\nmore text\nAI: Hello")
        self.assertEqual(turns, [{"role": "Student", "text": "Hi\nmore text"}, {"role": "AI", "text": "Hello"}])

    def test_parse_transcript_errors(self):
        for text in ("no label here", "Student: only student", "AI: only ai", "Student: \nAI: x"):
            with self.assertRaises(ValueError, msg=text):
                analysis.parse_transcript(text)

    def test_parse_transcript_requires_alternating_turns(self):
        with self.assertRaisesRegex(ValueError, "alternate"):
            analysis.parse_transcript("Student: a\nStudent: b\nAI: c")
        with self.assertRaisesRegex(ValueError, "Turns 2 and 3 are both AI"):
            analysis.parse_transcript("Student: a\nAI: b\nAI: c")
        self.assertEqual(len(analysis.parse_transcript("AI: hi\nStudent: a\nAI: b\nStudent: c")), 4)

    def test_every_synthetic_transcript_alternates(self):
        from seed_data import SEED_SUBMISSIONS
        for rec in SEED_SUBMISSIONS:
            roles = [t["role"] for t in rec["turns"]]
            self.assertTrue(all(a != b for a, b in zip(roles, roles[1:])), rec["ref"])

    def test_analysis_only_compares_wording_it_no_longer_judges_replies(self):
        turns = [{"role": "Student", "text": "Q"}, {"role": "AI", "text": "A"}, {"role": "Student", "text": "Thanks."}]
        result = analysis.analyze("My own words about something entirely different here.", turns)
        self.assertEqual(result["flags"], [])
        self.assertEqual(set(result), {"coverage", "paragraphs", "flags"})  # no keyword list, no phrase-list flags
        self.assertFalse(hasattr(analysis, "BRIEF_PHRASES") or hasattr(analysis, "REASONING_WORDS"))

    def test_missing_transcript_coverage(self):
        result = analysis.analyze("Some text.", [])
        self.assertEqual((result["flags"], result["coverage"]), ([], "Missing transcript"))

    def test_threshold_changes_flags(self):
        # Marker-visible example: SYN-107 has paragraphs scoring about 1.0, 0.69 and 0.52.
        from seed_data import SEED_SUBMISSIONS
        rec = next(r for r in SEED_SUBMISSIONS if r["ref"] == "SYN-107")
        counts = {t: len(analysis.analyze(rec["final_text"], rec["turns"], t)["flags"]) for t in (0.5, 0.65, 0.8)}
        self.assertEqual(counts, {0.5: 3, 0.65: 2, 0.8: 1})


class ContributionTests(unittest.TestCase):
    def test_identical_text_is_all_ai_matching(self):
        ai = "Solar panels can reduce a school's electricity costs by generating power during daylight hours."
        turns = [{"role": "Student", "text": "Q"}, {"role": "AI", "text": ai}]
        c = analysis.contribution(ai, turns)
        self.assertEqual((c["ai_percent"], c["other_percent"]), (100, 0))

    def test_unrelated_text_has_no_overlap(self):
        turns = [{"role": "Student", "text": "Q"}, {"role": "AI", "text": "Buses connect people to jobs and services every day."}]
        c = analysis.contribution("My own view is that cycling lanes deserve more funding than car parks.", turns)
        self.assertEqual(c["ai_percent"], 0)

    def test_segments_rebuild_the_original_text_and_mark_only_matches(self):
        ai = "the quick brown fox jumps over the lazy dog near the river bank"
        mine = "Honestly, the quick brown fox jumps over the lazy dog, and then I went home."
        c = analysis.contribution(mine, [{"role": "AI", "text": ai}])
        self.assertEqual("".join(s["text"] for s in c["paragraphs"][0]), mine)
        marked = "".join(s["text"] for s in c["paragraphs"][0] if s["ai"])
        self.assertEqual(marked, "the quick brown fox jumps over the lazy dog")
        self.assertEqual(c["ai_words"], 9)

    def test_no_transcript_means_zero(self):
        c = analysis.contribution("Some words here that are mine entirely.", [])
        self.assertEqual(c["ai_percent"], 0)

    def test_partial_copy_seed_record(self):
        from seed_data import SEED_SUBMISSIONS
        rec = next(r for r in SEED_SUBMISSIONS if r["ref"] == "SYN-107")
        c = analysis.contribution(rec["final_text"], rec["turns"])
        self.assertTrue(55 <= c["ai_percent"] <= 85, c["ai_percent"])


class SeedExpectationTests(unittest.TestCase):
    """Expected flags for every synthetic record, written down independently of the code."""
    WORDING = {  # wording comparison only (standard threshold)
        "SYN-101": {"overlap-0"}, "SYN-102": set(), "SYN-103": set(), "SYN-104": {"overlap-0"}, "SYN-105": set(),
        "SYN-106": set(), "SYN-107": {"overlap-0", "overlap-1"}, "SYN-108": set(), "SYN-109": set(), "SYN-110": set(),
        "SYN-111": set(), "SYN-112": {"overlap-0", "overlap-1"},
    }
    # With the stand-in critique check as well (blind acceptance replies are flagged by turn number).
    WITH_CRITIQUE = {**WORDING, "SYN-101": {"overlap-0", "critique-2"}, "SYN-104": {"overlap-0", "critique-2"},
                     "SYN-105": {"critique-2"}, "SYN-109": {"critique-2", "critique-4", "critique-6"},
                     "SYN-111": {"critique-2"}}

    def test_wording_flags_match_expected(self):
        from seed_data import SEED_SUBMISSIONS
        self.assertEqual({r["ref"] for r in SEED_SUBMISSIONS}, set(self.WORDING))
        for rec in SEED_SUBMISSIONS:
            keys = {f["key"] for f in analysis.analyze(rec["final_text"], rec["turns"])["flags"]}
            self.assertEqual(keys, self.WORDING[rec["ref"]], rec["ref"])

    def test_seeded_database_flags_match_expected_with_the_critique_check(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app({"DATABASE": os.path.join(d, "t.db"), "TESTING": True, "SECRET_KEY": "k"})
            marker = app.test_client()
            marker.post("/marker/login", data={"username": "marker1", "password": "marker-pass-1"})
            for ref, expected in self.WITH_CRITIQUE.items():
                flags = {f["id"] for f in marker.get(f"/api/submissions/{ref}").get_json()["analysis"]["flags"]}
                self.assertEqual(flags, expected, ref)


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.dir.name, "test.db")
        self.app = create_app({"DATABASE": self.db_path, "TESTING": True, "SECRET_KEY": "test-key"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.dir.cleanup()

    def login(self, role, username, password, client=None):
        return (client or self.client).post(f"/{role}/login", data={"username": username, "password": password})

    def submit(self, client=None, **overrides):
        body = {"topic": "Solar", "final_text": FINAL, "transcript": TRANSCRIPT}
        body.update(overrides)
        return (client or self.client).post("/api/student/submissions", json=body)


class AuthTests(AppTestCase):
    def test_wrong_password_rejected(self):
        res = self.login("student", "aiye355", "wrong")
        self.assertIn(b"Incorrect username or password.", res.data)
        self.assertEqual(self.client.get("/api/student/submissions").status_code, 401)

    def test_roles_cannot_use_other_login_page(self):
        self.assertIn(b"Incorrect", self.login("marker", "aiye355", "student-pass-1").data)
        self.assertIn(b"Incorrect", self.login("student", "marker1", "marker-pass-1").data)

    def test_anonymous_and_wrong_role_blocked(self):
        self.assertEqual(self.client.get("/api/submissions").status_code, 401)
        self.assertEqual(self.client.get("/marker").status_code, 302)
        self.login("student", "aiye355", "student-pass-1")
        self.assertEqual(self.client.get("/api/submissions").status_code, 403)
        self.assertEqual(self.client.get("/api/queue/export").status_code, 403)

    def test_passwords_are_hashed(self):
        import sqlite3
        row = sqlite3.connect(self.db_path).execute("SELECT password_hash FROM users WHERE username='aiye355'").fetchone()
        self.assertNotIn("student-pass-1", row[0])

    def test_logout_ends_session(self):
        self.login("marker", "marker1", "marker-pass-1")
        self.assertEqual(self.client.get("/api/submissions").status_code, 200)
        self.client.post("/logout")
        self.assertEqual(self.client.get("/api/submissions").status_code, 401)


class JourneyTests(AppTestCase):
    def test_student_submission_reaches_marker_queue_with_flags(self):
        self.login("student", "aiye355", "student-pass-1")
        res = self.submit()
        self.assertEqual(res.status_code, 201)
        ref = res.get_json()["ref"]
        self.assertEqual(ref, "SUB-013")

        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        queue = marker.get("/api/submissions").get_json()["submissions"]
        row = next(r for r in queue if r["ref"] == ref)
        self.assertEqual((row["turn_count"], row["flag_count"], row["status"]), (3, 2, "Not started"))
        record = marker.get(f"/api/submissions/{ref}").get_json()
        self.assertEqual({f["id"] for f in record["analysis"]["flags"]}, {"overlap-0", "critique-2"})

    def test_decisions_and_note_persist_after_restart(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        url = "/api/submissions/SYN-101"
        res = marker.put(f"{url}/flags/overlap-0/decision", json={"decision": "Accept flag", "rationale": "Verbatim."})
        self.assertEqual(res.status_code, 200)
        marker.put(f"{url}/note", json={"note": "Overall note."})
        # A brand new app object on the same database file: nothing is held in memory.
        again = create_app({"DATABASE": self.db_path, "TESTING": True, "SECRET_KEY": "test-key"}).test_client()
        self.login("marker", "marker1", "marker-pass-1", again)
        record = again.get(url).get_json()
        self.assertEqual(record["decisions"]["overlap-0"]["rationale"], "Verbatim.")
        self.assertEqual((record["note"], record["status"]), ("Overall note.", "In progress"))

    def test_completion_rules_and_success(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        url = "/api/submissions/SYN-105"  # one flag: critique-2 ("Thanks!")
        self.assertEqual(marker.post(f"{url}/complete").status_code, 400)  # no note
        marker.put(f"{url}/note", json={"note": "Note."})
        self.assertEqual(marker.post(f"{url}/complete").status_code, 400)  # flag undecided
        marker.put(f"{url}/flags/critique-2/decision", json={"decision": "Need more context", "rationale": "Unsure."})
        self.assertIn("Need more context", marker.post(f"{url}/complete").get_json()["error"])
        marker.put(f"{url}/flags/critique-2/decision", json={"decision": "Dismiss flag", "rationale": "Polite reply."})
        self.assertEqual(marker.post(f"{url}/complete").status_code, 200)
        self.assertEqual(marker.get(url).get_json()["status"], "Reviewed")

    def test_missing_transcript_blocks_completion(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        marker.put("/api/submissions/SYN-103/note", json={"note": "Note."})
        self.assertEqual(marker.post("/api/submissions/SYN-103/complete").status_code, 400)

    def test_decision_validation(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        base = "/api/submissions/SYN-101/flags/overlap-0/decision"
        self.assertEqual(marker.put(base, json={"decision": "Bogus", "rationale": "x"}).status_code, 400)
        self.assertEqual(marker.put(base, json={"decision": "Dismiss flag", "rationale": "  "}).status_code, 400)
        self.assertEqual(marker.put("/api/submissions/SYN-101/flags/nope/decision",
                                    json={"decision": "Dismiss flag", "rationale": "x"}).status_code, 404)

    def test_review_threshold_is_not_exposed_or_changeable(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        self.assertEqual(marker.post("/api/threshold", json={"value": 0.5}).status_code, 404)
        queue = marker.get("/api/submissions").get_json()
        self.assertNotIn("threshold", queue)
        # the standard threshold (65%) is applied in the background: SYN-107 has flags at 100% and 69% only
        flags = {r["ref"]: r["flag_count"] for r in queue["submissions"]}
        self.assertEqual(flags["SYN-107"], 2)

    def test_review_export_is_a_readable_pdf(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        marker.put("/api/submissions/SYN-101/flags/overlap-0/decision", json={"decision": "Accept flag", "rationale": "Verbatim copy."})
        marker.put("/api/submissions/SYN-101/note", json={"note": "Overall note for the PDF."})
        res = marker.get("/api/submissions/SYN-101/export")
        self.assertEqual((res.status_code, res.mimetype), (200, "application/pdf"))
        self.assertTrue(res.data.startswith(b"%PDF-"))
        self.assertIn("aiye355-SYN-101-review.pdf", res.headers["Content-Disposition"])
        from test_pdf import pdf_text
        text = pdf_text(res.data)
        for expected in ("Review report", "aiye355", "Community energy grants", "Accept flag", "Verbatim copy.",
                         "Recorded by marker1", "Overall note for the PDF.", "Full interaction history",
                         "Explain community solar grants for schools.", "Good answer."):
            self.assertIn(expected, text)

    def test_queue_export_is_csv(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        csv_res = marker.get("/api/queue/export")
        self.assertIn("attachment", csv_res.headers["Content-Disposition"])
        self.assertIn('"SYN-101"', csv_res.get_data(as_text=True))

    def test_csv_formula_guard(self):
        from app import csv_safe
        self.assertEqual(csv_safe("=1+1"), "'=1+1")
        self.assertEqual(csv_safe("Plain"), "Plain")


class AccountTests(AppTestCase):
    def test_new_student_logins_work_with_original_passwords(self):
        for username, password in (("aiye355", "student-pass-1"), ("hluo185", "student-pass-2"),
                                   ("acoa536", "student-pass-3"), ("hcoo867", "student-pass-4")):
            client = self.app.test_client()
            res = self.login("student", username, password, client)
            self.assertEqual(res.status_code, 302, username)
            self.assertEqual(client.get("/student").status_code, 200, username)

    def test_old_usernames_no_longer_exist(self):
        for username in ("student1", "student2", "student3"):
            self.assertIn(b"Incorrect", self.login("student", username, "student-pass-1").data)

    def test_submitters_without_a_login_cannot_sign_in(self):
        for username in ("rnav609", "kugn020"):
            for password in ("", "student-pass-5", "student-pass-6", "password"):
                self.assertIn(b"Incorrect", self.login("student", username, password).data)

    def test_usernames_shown_on_pages(self):
        self.login("student", "acoa536", "student-pass-3")
        page = self.client.get("/student").get_data(as_text=True)
        self.assertIn("acoa536", page)
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        self.assertIn("marker1", marker.get("/marker").get_data(as_text=True))

    def test_queue_uses_student_usernames(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        rows = marker.get("/api/submissions").get_json()["submissions"]
        owners = {r["ref"]: r["student"] for r in rows}
        self.assertEqual(owners["SYN-101"], "aiye355")
        self.assertEqual(owners["SYN-103"], "hcoo867")
        self.assertEqual(owners["SYN-104"], "acoa536")
        self.assertEqual({r["student"] for r in rows},
                         {"aiye355", "hluo185", "hcoo867", "acoa536", "rnav609", "kugn020"})
        self.assertEqual(marker.get("/api/submissions/SYN-101").get_json()["student"], "aiye355")

    def test_flag_explanations_use_short_wording(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        flags = {f["id"]: f for f in marker.get("/api/submissions/SYN-101").get_json()["analysis"]["flags"]}
        self.assertEqual(flags["overlap-0"]["reason"], "The paragraph matches AI turn 2 under the five-word "
                         "phrase rule. Read the surrounding interaction before interpreting this flag.")
        self.assertEqual((flags["critique-2"]["type"], flags["critique-2"]["origin"]), ("Critique quality", "llm"))
        self.assertNotIn("response-2", flags)

    def test_export_filename_uses_username(self):
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        res = marker.get("/api/submissions/SYN-101/export")
        self.assertIn("aiye355-SYN-101-review.pdf", res.headers["Content-Disposition"])


class UpgradeTests(unittest.TestCase):
    def test_older_database_is_backed_up_and_replaced(self):
        import glob
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "lane2.db")
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE users (id INTEGER, username TEXT)")
            conn.execute("INSERT INTO users VALUES (1, 'student1')")
            conn.commit()
            conn.close()
            app = create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
            backups = glob.glob(os.path.join(d, "lane2.backup-*.db"))
            self.assertEqual(len(backups), 1)
            old = sqlite3.connect(backups[0]).execute("SELECT username FROM users").fetchall()
            self.assertEqual(old, [("student1",)])  # nothing was lost
            names = {r[0] for r in sqlite3.connect(path).execute("SELECT username FROM users")}
            self.assertIn("aiye355", names)
            self.assertNotIn("student1", names)

    def test_current_database_is_left_alone(self):
        import glob
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "lane2.db")
            create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
            create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
            self.assertEqual(glob.glob(os.path.join(d, "lane2.backup-*.db")), [])


class InPlaceUpgradeTests(unittest.TestCase):
    """Older databases (data versions 2.2 and 2.3) are upgraded without losing the team's data."""

    OLD_FLAGS = ("CREATE TABLE flags (id INTEGER PRIMARY KEY AUTOINCREMENT, submission_id INTEGER NOT NULL REFERENCES "
                 "submissions(id) ON DELETE CASCADE, flag_key TEXT NOT NULL, type TEXT NOT NULL CHECK (type IN "
                 "('Text overlap', 'Brief acceptance', 'Critique quality')), origin TEXT NOT NULL DEFAULT 'rule', "
                 "verdict TEXT, quote TEXT, paragraph INTEGER, turn_index INTEGER NOT NULL, score REAL, "
                 "source_text TEXT NOT NULL, target_text TEXT NOT NULL, reason TEXT NOT NULL, UNIQUE (submission_id, flag_key))")

    def build_old_database(self, path, version):
        """Make a database that looks like one created by an older version of the project."""
        import sqlite3
        app = create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
        student = app.test_client()
        student.post("/student/login", data={"username": "aiye355", "password": "student-pass-1"})
        ref = student.post("/api/student/submissions", json={
            "topic": "Kept topic", "final_text": "My own words about energy.",
            "transcript": "Student: Q\nAI: A\nStudent: Thanks"}).get_json()["ref"]
        marker = app.test_client()
        marker.post("/marker/login", data={"username": "marker1", "password": "marker-pass-1"})
        marker.put("/api/submissions/SYN-101/flags/overlap-0/decision", json={"decision": "Accept flag", "rationale": "Old reason."})
        marker.put("/api/submissions/SYN-101/flags/critique-2/decision", json={"decision": "Dismiss flag", "rationale": "Polite."})
        marker.put("/api/submissions/SYN-102/note", json={"note": "Old note."})
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = OFF")
        flags = conn.execute("SELECT * FROM flags").fetchall()
        flag_cols = [c[1] for c in conn.execute("PRAGMA table_info(flags)")]
        decisions = conn.execute("SELECT id, flag_id, marker_id, decision, rationale, decided_at FROM decisions").fetchall()
        # the old rule-based flag on SYN-101's "Good answer." reply, with the label the old version used
        sid = conn.execute("SELECT id FROM submissions WHERE ref='SYN-101'").fetchone()[0]
        conn.execute("DROP TABLE decisions")
        conn.execute("DROP TABLE flags")
        conn.execute(self.OLD_FLAGS)
        idx = {c: i for i, c in enumerate(flag_cols)}
        for row in flags:
            conn.execute("INSERT INTO flags VALUES (%s)" % ",".join("?" * len(flag_cols)),
                         [row[idx[c]] for c in ("id", "submission_id", "flag_key", "type", "origin", "verdict", "quote",
                                                 "paragraph", "turn_index", "score", "source_text", "target_text", "reason")])
        conn.execute("DELETE FROM flags WHERE submission_id=? AND flag_key='critique-2'", (sid,))
        conn.execute("INSERT INTO flags (submission_id, flag_key, type, origin, turn_index, source_text, target_text, reason)"
                     " VALUES (?, 'response-2', 'Brief acceptance', 'rule', 2, 'A', 'Good answer.', 'old rule')", (sid,))
        old_flag = conn.execute("SELECT id FROM flags WHERE submission_id=? AND flag_key='response-2'", (sid,)).fetchone()[0]
        label = "Relevant for assessment" if version == "2.2" else "Accept flag"
        conn.execute("CREATE TABLE decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, flag_id INTEGER NOT NULL UNIQUE "
                     "REFERENCES flags(id) ON DELETE CASCADE, marker_id INTEGER NOT NULL REFERENCES users(id), "
                     f"decision TEXT NOT NULL CHECK (decision IN ('{label}', 'Dismiss flag', 'Need more context')), "
                     "rationale TEXT NOT NULL, decided_at TEXT NOT NULL)")
        kept = [d for d in decisions if conn.execute("SELECT 1 FROM flags WHERE id=?", (d[1],)).fetchone()]
        for i, f, m, dec, r, at in kept:
            conn.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?)", (i, f, m, label if dec == "Accept flag" else dec, r, at))
        conn.execute("INSERT INTO decisions (flag_id, marker_id, decision, rationale, decided_at) VALUES (?,1,'Dismiss flag','Polite old-rule flag.','2026-10-01T00:00:00+00:00')", (old_flag,))
        if version == "2.2":
            sid4 = conn.execute("SELECT id FROM submissions WHERE ref='SYN-104'").fetchone()[0]
            conn.execute("DELETE FROM turns WHERE submission_id=?", (sid4,))
            old = [("Student", "Explain access benefits of buses."), ("AI", "Better bus services can improve access to employment "
                   "and education. Outcomes depend on frequency, reliability, route coverage and affordability. A transport policy "
                   "should evaluate these factors before projecting changes in ridership."), ("Student", "I agree."),
                   ("Student", "However, I need to verify the evidence for ridership changes.")]
            for i, (role, text) in enumerate(old):
                conn.execute("INSERT INTO turns (submission_id, position, role, text) VALUES (?,?,?,?)", (sid4, i, role, text))
        conn.execute("UPDATE settings SET value=? WHERE key='seed_version'", (version,))
        conn.commit()
        conn.close()
        return ref

    def check_upgrade(self, version):
        import glob
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "lane2.db")
            ref = self.build_old_database(path, version)
            app = create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
            backups = glob.glob(os.path.join(d, "lane2.backup-*.db"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(sqlite3.connect(backups[0]).execute("SELECT value FROM settings WHERE key='seed_version'").fetchone()[0], version)
            marker = app.test_client()
            marker.post("/marker/login", data={"username": "marker1", "password": "marker-pass-1"})
            record = marker.get("/api/submissions/SYN-101").get_json()
            ids = [f["id"] for f in record["analysis"]["flags"]]
            self.assertEqual(ids, ["overlap-0", "critique-2"])      # old phrase-list flag gone, critique flag in its place
            self.assertEqual(record["decisions"]["overlap-0"], {"decision": "Accept flag", "rationale": "Old reason."})
            self.assertNotIn("critique-2", record["decisions"])     # the new flag needs a fresh decision
            self.assertEqual(marker.get("/api/submissions/SYN-102").get_json()["note"], "Old note.")
            self.assertEqual(marker.get(f"/api/submissions/{ref}").get_json()["topic"], "Kept topic")
            self.assertEqual(sqlite3.connect(path).execute("SELECT value FROM settings WHERE key='seed_version'").fetchone()[0], "2.4")
            if version == "2.2":
                roles = [t["role"] for t in marker.get("/api/submissions/SYN-104").get_json()["turns"]]
                self.assertEqual(roles, ["Student", "AI", "Student", "AI", "Student"])
            # the upgraded database accepts new decisions and has the new schema
            res = marker.put("/api/submissions/SYN-101/flags/critique-2/decision", json={"decision": "Accept flag", "rationale": "x"})
            self.assertEqual(res.status_code, 200)

    def test_upgrade_from_2_3_keeps_data_and_replaces_phrase_flags(self):
        self.check_upgrade("2.3")

    def test_upgrade_from_2_2_also_renames_decisions_and_fixes_syn104(self):
        self.check_upgrade("2.2")

    def test_reviewed_status_is_reopened_when_new_flags_need_decisions(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "lane2.db")
            self.build_old_database(path, "2.3")
            conn = sqlite3.connect(path)
            conn.execute("UPDATE submissions SET status='Reviewed' WHERE ref='SYN-101'")
            conn.commit()
            conn.close()
            app = create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
            marker = app.test_client()
            marker.post("/marker/login", data={"username": "marker1", "password": "marker-pass-1"})
            self.assertEqual(marker.get("/api/submissions/SYN-101").get_json()["status"], "In progress")

    def test_upgrade_runs_only_once(self):
        import glob
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "lane2.db")
            self.build_old_database(path, "2.3")
            create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
            create_app({"DATABASE": path, "TESTING": True, "SECRET_KEY": "k"})
            self.assertEqual(len(glob.glob(os.path.join(d, "lane2.backup-*.db"))), 1)


class StudentValidationTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login("student", "aiye355", "student-pass-1")

    def test_validation_errors(self):
        cases = [
            ({"topic": " "}, "topic"),
            ({"final_text": ""}, "topic"),
            ({"transcript": ""}, "Paste your AI"),
            ({"transcript": "Student: only me"}, "at least one"),
            ({"transcript": "free text"}, "Start each turn"),
            ({"transcript": "Student: a\nAI: "}, "needs text"),
            ({"topic": "x" * 101}, "Topic exceeds"),
            ({"final_text": "x" * 20001}, "Submission exceeds"),
            ({"transcript": "Student: a\nAI: " + "x" * 30001}, "Transcript exceeds"),
        ]
        for overrides, fragment in cases:
            res = self.submit(**overrides)
            self.assertEqual(res.status_code, 400, overrides)
            self.assertIn(fragment, res.get_json()["error"], overrides)

    def test_no_fictional_data_confirmation_is_needed(self):
        res = self.client.post("/api/student/submissions", json={"topic": "T", "final_text": "Some words of my own here.",
                                                                  "transcript": TRANSCRIPT})
        self.assertEqual(res.status_code, 201)

    def test_turns_must_alternate(self):
        bad = ("Student: Q\nAI: A\nStudent: first\nStudent: second", "AI: A\nAI: B\nStudent: S", "Student: a\nStudent: b\nAI: c")
        for transcript in bad:
            res = self.submit(transcript=transcript)
            self.assertEqual(res.status_code, 400, transcript)
            self.assertIn("alternate", res.get_json()["error"])
        ok = self.submit(transcript="AI: Hello, how can I help?\nStudent: Explain solar panels.\nAI: They turn sunlight into power.")
        self.assertEqual(ok.status_code, 201)

    def test_transcript_added_later_must_alternate(self):
        ref = self.submit(transcript="", no_transcript=True).get_json()["ref"]
        res = self.client.post(f"/api/student/submissions/{ref}/transcript", json={"transcript": "Student: a\nStudent: b\nAI: c"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("alternate", res.get_json()["error"])

    def test_critique_check_applies_to_every_new_submission_and_no_keyword_list_remains(self):
        transcript = ("Student: Explain bus access.\nAI: Buses help people reach jobs.\n"
                      "Student: However, I need evidence because that claim seems too broad.\nAI: Fair point.\n"
                      "Student: Thanks.")
        ref = self.submit(transcript=transcript).get_json()["ref"]
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        record = marker.get(f"/api/submissions/{ref}").get_json()
        self.assertNotIn("cues", record["analysis"])
        verdicts = {a["turn"]: a["verdict"] for a in record["critique_check"]["assessments"]}
        self.assertEqual(verdicts, {3: "substantive", 5: "blind_acceptance"})
        self.assertEqual([f["id"] for f in record["analysis"]["flags"]], ["critique-4"])

    def test_no_transcript_checkbox_creates_missing_transcript_case(self):
        ref = self.submit(transcript="", no_transcript=True).get_json()["ref"]
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        self.assertEqual(marker.get(f"/api/submissions/{ref}").get_json()["analysis"]["coverage"], "Missing transcript")

    def test_transcript_can_be_added_once_by_owner_only(self):
        ref = self.submit(transcript="", no_transcript=True).get_json()["ref"]
        other = self.app.test_client()
        self.login("student", "hluo185", "student-pass-2", other)
        self.assertEqual(other.post(f"/api/student/submissions/{ref}/transcript", json={"transcript": TRANSCRIPT}).status_code, 404)
        self.assertEqual(self.client.post(f"/api/student/submissions/{ref}/transcript", json={"transcript": "bad"}).status_code, 400)
        ok = self.client.post(f"/api/student/submissions/{ref}/transcript", json={"transcript": TRANSCRIPT})
        self.assertEqual(ok.status_code, 200)
        again = self.client.post(f"/api/student/submissions/{ref}/transcript", json={"transcript": TRANSCRIPT})
        self.assertEqual(again.status_code, 409)

    def test_students_see_only_their_own_submissions(self):
        mine = {s["ref"] for s in self.client.get("/api/student/submissions").get_json()["submissions"]}
        self.assertEqual(mine, {"SYN-101", "SYN-107"})

    def test_html_in_submission_is_stored_as_text(self):
        ref = self.submit(topic="<script>alert(1)</script>").get_json()["ref"]
        marker = self.app.test_client()
        self.login("marker", "marker1", "marker-pass-1", marker)
        self.assertEqual(marker.get(f"/api/submissions/{ref}").get_json()["topic"], "<script>alert(1)</script>")


if __name__ == "__main__":
    unittest.main()
