"""Lane 2 Evidence Review - Flask backend (version 2).

Run with:   python app.py
Then open:  http://127.0.0.1:5000

Structure of this file
    1. Configuration and database helpers
    2. Analysis helpers (store flags, build records for the marker)
    3. Login / logout and page routes
    4. Student API (submit work, add a missing transcript)
    5. Marker API (queue, review, decisions, notes, completion, PDF and CSV exports)
"""
import csv
import io
import json
import os
import secrets
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (Flask, Response, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import analysis
import llm_flags
import pdf_report
from seed_data import SEED_SUBMISSIONS, SEED_USERS, SEED_VERSION

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DECISIONS = ("Accept flag", "Dismiss flag", "Need more context")
MIGRATABLE_VERSIONS = ("2.2", "2.3")   # older data versions that are upgraded in place, keeping everything
MAX_TOPIC, MAX_FINAL, MAX_TRANSCRIPT = 100, 20000, 30000
MAX_RATIONALE, MAX_NOTE = 2000, 5000


# --------------------------------------------------------------------------- #
# 1. Configuration and database helpers
# --------------------------------------------------------------------------- #
def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(
        DATABASE=os.environ.get("LANE2_DATABASE_PATH", os.path.join(app.instance_path, "lane2.db")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1_000_000,
    )
    if config:
        app.config.update(config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = load_secret_key(app)

    app.teardown_appcontext(close_db)
    app.after_request(add_security_headers)
    register_routes(app)
    ensure_current_database(app.config["DATABASE"])
    with app.app_context():
        init_db()
    return app


def load_secret_key(app):
    """Use LANE2_SECRET_KEY if set, otherwise create and reuse instance/secret.key."""
    env = os.environ.get("LANE2_SECRET_KEY")
    if env:
        return env
    path = os.path.join(app.instance_path, "secret.key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


def ensure_current_database(path):
    """Keep an existing database usable across versions.

    * Same data version: nothing to do.
    * A version listed in MIGRATABLE_VERSIONS: a copy is saved first, then init_db() upgrades the
      database in place, so submissions, transcripts and decisions are kept.
    * Any other version: the old file is moved to lane2.backup-<time>.db and a fresh one is built.
    Nothing is ever deleted.
    """
    if not os.path.exists(path):
        return
    version = None
    try:
        conn = sqlite3.connect(path)
        row = conn.execute("SELECT value FROM settings WHERE key='seed_version'").fetchone()
        version = row[0] if row else None
        conn.close()
    except sqlite3.Error:
        version = None
    if version == SEED_VERSION:
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(os.path.dirname(path), f"lane2.backup-{stamp}.db")
    if version in MIGRATABLE_VERSIONS:
        shutil.copy2(path, backup)
        print(f"Existing database upgraded in place. A copy of the old one was saved as {backup}.")
    else:
        shutil.move(path, backup)
        print(f"Existing database was from an older version. It was saved as {backup} and a new one was created.")


def get_db():
    from flask import current_app
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def replace_syn104_transcript(db):
    """Version 2.2 data only: SYN-104 had two Student turns in a row. Replace it with the alternating version."""
    record = next(r for r in SEED_SUBMISSIONS if r["ref"] == "SYN-104")
    row = db.execute("SELECT id, final_text FROM submissions WHERE ref='SYN-104'").fetchone()
    if row is None or row["final_text"] != record["final_text"] or len(load_turns(db, row["id"])) != 4:
        return
    store_turns(db, row["id"], record["turns"])
    save_llm_run(db, row["id"], llm_flags.assess(record["turns"], allow_live=False))


DECISION_RENAMES = {"Relevant for assessment": "Accept flag"}  # label used before data version 2.3


def upgrade_flags_and_decisions(db, old_version):
    """Upgrade data version 2.2 or 2.3 to 2.4 in place, keeping what the team has entered.

    Flags are derived data (wording comparison plus the stored critique check), so they are simply
    rebuilt. Decisions are kept for every flag that still exists. What changed:
      * 2.2: "Relevant for assessment" became "Accept flag"; SYN-104 got an alternating transcript.
      * 2.3: the phrase-list rule (brief acceptance) and the keyword list were removed, because the
        critique check judges every student reply. Decisions saved on the removed phrase-list flags
        cannot be kept. The critique check's own flags (from its stored result) replace them.
    """
    saved = [dict(r) for r in db.execute(
        "SELECT s.ref, f.flag_key, d.marker_id, d.decision, d.rationale, d.decided_at FROM decisions d"
        " JOIN flags f ON f.id=d.flag_id JOIN submissions s ON s.id=f.submission_id").fetchall()]
    if old_version == "2.2":
        replace_syn104_transcript(db)
    db.execute("DROP TABLE decisions")
    db.execute("DROP TABLE flags")
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())
    for row in db.execute("SELECT id, final_text FROM submissions").fetchall():
        store_flags(db, row["id"], row["final_text"], load_turns(db, row["id"]))
    lost = 0
    for d in saved:
        flag = db.execute(
            "SELECT f.id FROM flags f JOIN submissions s ON s.id=f.submission_id WHERE s.ref=? AND f.flag_key=?",
            (d["ref"], d["flag_key"])).fetchone()
        if flag is None:
            lost += 1
            continue
        db.execute("INSERT INTO decisions (flag_id, marker_id, decision, rationale, decided_at) VALUES (?,?,?,?,?)",
                   (flag["id"], d["marker_id"], DECISION_RENAMES.get(d["decision"], d["decision"]),
                    d["rationale"], d["decided_at"]))
    # A review marked Reviewed must still be complete. If new flags need a decision, it goes back to In progress.
    for row in db.execute("SELECT id FROM submissions WHERE status='Reviewed'").fetchall():
        open_flags = db.execute(
            "SELECT COUNT(*) FROM flags f LEFT JOIN decisions d ON d.flag_id=f.id WHERE f.submission_id=?"
            " AND (d.id IS NULL OR d.decision='Need more context')", (row["id"],)).fetchone()[0]
        if open_flags:
            db.execute("UPDATE submissions SET status='In progress' WHERE id=?", (row["id"],))
    if lost:
        print(f"{lost} saved decision(s) were on flags from the removed phrase-list rule and could not be kept.")


def init_db():
    """Create tables if needed, upgrade an older database, and load the synthetic data on first run."""
    db = get_db()
    old_version = None
    try:
        row = db.execute("SELECT value FROM settings WHERE key='seed_version'").fetchone()
        old_version = row[0] if row else None
    except sqlite3.OperationalError:
        pass  # a brand new database has no settings table yet
    if old_version in MIGRATABLE_VERSIONS:
        upgrade_flags_and_decisions(db, old_version)
    else:
        with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
            db.executescript(f.read())
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('seed_version', ?)", (SEED_VERSION,))
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        for username, password, role, display in SEED_USERS:
            # No password given: create a random one that nobody knows, so there is no login.
            password = password or secrets.token_urlsafe(24)
            db.execute(
                "INSERT INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)",
                (username, generate_password_hash(password), role, display))
        for rec in SEED_SUBMISSIONS:
            student = db.execute("SELECT id FROM users WHERE username=?", (rec["student"],)).fetchone()
            # Seed data uses saved results only (llm_cache.json); no OpenAI call at start-up.
            assessment = llm_flags.assess(rec["turns"], allow_live=False)
            insert_submission(db, student["id"], rec["topic"], rec["final_text"], rec["turns"], assessment,
                              ref=rec["ref"], submitted_at=rec["submitted_at"])
    db.commit()


def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'")
    if request.path.startswith("/api/") or not request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# --------------------------------------------------------------------------- #
# 2. Analysis helpers
# --------------------------------------------------------------------------- #
def store_turns(db, submission_id, turns):
    db.execute("DELETE FROM turns WHERE submission_id=?", (submission_id,))
    for position, t in enumerate(turns):
        db.execute("INSERT INTO turns (submission_id, position, role, text) VALUES (?,?,?,?)",
                   (submission_id, position, t["role"], t["text"]))


def latest_llm_run(db, submission_id):
    return db.execute("SELECT * FROM llm_runs WHERE submission_id=? ORDER BY id DESC LIMIT 1",
                      (submission_id,)).fetchone()


def save_llm_run(db, submission_id, assessment):
    """Record what happened when the critique check was run (never includes the API key)."""
    result = {"assessments": assessment["assessments"], "rejected": assessment["rejected"]}
    db.execute(
        "INSERT INTO llm_runs (submission_id, status, mode, model, rubric_version, error, result_json, created_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (submission_id, assessment["status"], assessment["mode"], assessment["model"],
         assessment["rubric_version"], assessment["error"], json.dumps(result), now()))


def live_calls_ok(db):
    """A simple cost guard: limit live OpenAI calls per hour (default 30)."""
    try:
        limit = int(os.environ.get("LANE2_LLM_HOURLY_LIMIT", "30"))
    except ValueError:
        limit = 30
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    used = db.execute("SELECT COUNT(*) FROM llm_runs WHERE mode='live' AND created_at>=?", (since,)).fetchone()[0]
    return used < limit


def store_flags(db, submission_id, final_text, turns):
    """Rebuild this submission's stored flags: wording overlap plus the newest critique check.

    Deleting a flag also deletes its decision (ON DELETE CASCADE), so any change to the
    evidence clears decisions, as in version 1. No OpenAI call is made here:
    critique flags are rebuilt from the stored result of the last check.
    """
    db.execute("DELETE FROM flags WHERE submission_id=?", (submission_id,))
    result = analysis.analyze(final_text, turns, analysis.DEFAULT_THRESHOLD)
    for f in result["flags"]:
        db.execute(
            "INSERT INTO flags (submission_id, flag_key, type, paragraph, turn_index, score,"
            " source_text, target_text, reason) VALUES (?,?,?,?,?,?,?,?,?)",
            (submission_id, f["key"], f["type"], f["paragraph"], f["turn"], f["score"],
             f["source"], f["target"], f["reason"]))
    run = latest_llm_run(db, submission_id)
    if run is None or run["status"] != "ok":
        return
    for a in json.loads(run["result_json"])["assessments"]:
        i = a["index"]
        if a["verdict"] not in llm_flags.FLAG_VERDICTS or not 0 < i < len(turns):
            continue
        db.execute(
            "INSERT INTO flags (submission_id, flag_key, type, paragraph, turn_index, score, source_text,"
            " target_text, reason, origin, verdict, quote) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (submission_id, f"critique-{i}", "Critique quality", None, i, None, turns[i - 1]["text"],
             turns[i]["text"], a["reason"], "llm", a["verdict"], a["quote"]))


def rebuild_keeping_decisions(db, submission_id, final_text, turns):
    """Rebuild flags but keep decisions for flags that still exist (used when a check is re-run)."""
    saved = db.execute(
        "SELECT f.flag_key, d.marker_id, d.decision, d.rationale, d.decided_at FROM decisions d"
        " JOIN flags f ON f.id=d.flag_id WHERE f.submission_id=?", (submission_id,)).fetchall()
    store_flags(db, submission_id, final_text, turns)
    for d in saved:
        flag = db.execute("SELECT id FROM flags WHERE submission_id=? AND flag_key=?",
                          (submission_id, d["flag_key"])).fetchone()
        if flag:
            db.execute("INSERT INTO decisions (flag_id, marker_id, decision, rationale, decided_at) VALUES (?,?,?,?,?)",
                       (flag["id"], d["marker_id"], d["decision"], d["rationale"], d["decided_at"]))


def insert_submission(db, student_id, topic, final_text, turns, assessment, ref=None, submitted_at=None):
    """Insert a submission, its turns, its critique check and its flags. Returns the new ref.

    `assessment` is the result of llm_flags.assess(), computed BEFORE this function is called so
    that no database lock is held while waiting for OpenAI.
    """
    temp_ref = ref or "PENDING-" + uuid.uuid4().hex
    cur = db.execute(
        "INSERT INTO submissions (ref, student_id, topic, final_text, submitted_at) VALUES (?,?,?,?,?)",
        (temp_ref, student_id, topic, final_text, submitted_at or now()))
    sid = cur.lastrowid
    if ref is None:
        ref = f"SUB-{sid:03d}"
        db.execute("UPDATE submissions SET ref=? WHERE id=?", (ref, sid))
    store_turns(db, sid, turns)
    save_llm_run(db, sid, assessment)
    store_flags(db, sid, final_text, turns)
    return ref


def load_turns(db, submission_id):
    rows = db.execute("SELECT role, text FROM turns WHERE submission_id=? ORDER BY position",
                      (submission_id,)).fetchall()
    return [{"role": r["role"], "text": r["text"]} for r in rows]


def build_record(db, row):
    """Everything the marker page needs for one submission."""
    turns = load_turns(db, row["id"])
    structure = analysis.structure(row["final_text"], turns)
    flag_rows = db.execute(
        "SELECT f.*, d.decision, d.rationale FROM flags f LEFT JOIN decisions d ON d.flag_id=f.id"
        " WHERE f.submission_id=? ORDER BY f.id", (row["id"],)).fetchall()
    run = latest_llm_run(db, row["id"])
    check = {"status": "not_run", "mode": "none", "model": None, "rubric_version": llm_flags.RUBRIC_VERSION,
             "error": None, "rejected": 0, "assessments": []}
    if run is not None:
        result = json.loads(run["result_json"])
        check.update(status=run["status"], mode=run["mode"], model=run["model"], error=run["error"],
                     rubric_version=run["rubric_version"], rejected=len(result["rejected"]),
                     assessments=result["assessments"])
    flags, decisions = [], {}
    for f in flag_rows:
        flags.append({"id": f["flag_key"], "type": f["type"], "paragraph": f["paragraph"],
                      "turn": f["turn_index"], "score": f["score"], "source": f["source_text"],
                      "target": f["target_text"], "reason": f["reason"], "origin": f["origin"],
                      "verdict": f["verdict"], "quote": f["quote"]})
        if f["decision"]:
            decisions[f["flag_key"]] = {"decision": f["decision"], "rationale": f["rationale"]}
    student = db.execute("SELECT username FROM users WHERE id=?", (row["student_id"],)).fetchone()
    return {
        "id": row["ref"], "topic": row["topic"], "submission": row["final_text"], "turns": turns,
        "status": row["status"], "note": row["overall_note"], "decisions": decisions,
        "student": student["username"], "submitted_at": row["submitted_at"],
        "analysis": {"flags": flags, "coverage": structure["coverage"],
                     "paragraphs": structure["paragraphs"]},
        "critique_check": check,
        "contribution": analysis.contribution(row["final_text"], turns),
    }


def get_submission_or_404(db, ref):
    return db.execute("SELECT * FROM submissions WHERE ref=?", (ref,)).fetchone()


def validate_submission(data):
    """Server-side validation of a student's submission. Raises ValueError."""
    topic = str(data.get("topic", "")).strip()
    final_text = str(data.get("final_text", "")).replace("\r\n", "\n").strip()
    transcript = str(data.get("transcript", "")).replace("\r\n", "\n")
    if not topic or not final_text:
        raise ValueError("Enter a topic and your final submission.")
    if len(topic) > MAX_TOPIC:
        raise ValueError(f"Topic exceeds {MAX_TOPIC} characters.")
    if len(final_text) > MAX_FINAL:
        raise ValueError(f"Submission exceeds {MAX_FINAL:,} characters.")
    if len(transcript) > MAX_TRANSCRIPT:
        raise ValueError(f"Transcript exceeds {MAX_TRANSCRIPT:,} characters.")
    if transcript.strip():
        turns = analysis.parse_transcript(transcript)
    elif data.get("no_transcript") is True:
        turns = []
    else:
        raise ValueError("Paste your AI interaction history, or tick the box to say you have none.")
    return topic, final_text, turns


# --------------------------------------------------------------------------- #
# 3. Authentication and routes
# --------------------------------------------------------------------------- #
def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def require(role, api=False):
    """Allow a route only for a signed-in user with this role."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                if api:
                    return jsonify(error="Please sign in."), 401
                return redirect(url_for(f"{role}_login"))
            if user["role"] != role:
                if api:
                    return jsonify(error="You do not have access to this."), 403
                return redirect(url_for(f"{user['role']}_home"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def csv_safe(value):
    """Stop spreadsheet programs treating exported text as a formula."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "@", "-") else text


def register_routes(app):
    # ---- pages ----------------------------------------------------------- #
    @app.get("/")
    def landing():
        user = current_user()
        if user:
            return redirect(url_for(f"{user['role']}_home"))
        return render_template("landing.html")

    def login_view(role):
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute("SELECT * FROM users WHERE username=? AND role=?",
                                    (username, role)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for(f"{role}_home"))
            error = "Incorrect username or password."
        return render_template("login.html", role=role, error=error)

    @app.route("/student/login", methods=["GET", "POST"])
    def student_login():
        return login_view("student")

    @app.route("/marker/login", methods=["GET", "POST"])
    def marker_login():
        return login_view("marker")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("landing"))

    @app.get("/student")
    @require("student")
    def student_home():
        return render_template("student.html", user=current_user())

    @app.get("/marker")
    @require("marker")
    def marker_home():
        return render_template("marker.html", user=current_user())

    # ---- student API ----------------------------------------------------- #
    @app.post("/api/student/submissions")
    @require("student", api=True)
    def student_submit():
        try:
            topic, final_text, turns = validate_submission(json_body())
        except ValueError as err:
            return jsonify(error=str(err)), 400
        db = get_db()
        # Ask OpenAI (or use the cache) first, so no database lock is held while waiting.
        assessment = llm_flags.assess(turns, allow_live=True, usage_ok=live_calls_ok(db))
        ref = insert_submission(db, current_user()["id"], topic, final_text, turns, assessment)
        db.commit()
        return jsonify(ref=ref), 201

    @app.get("/api/student/submissions")
    @require("student", api=True)
    def student_list():
        rows = get_db().execute(
            "SELECT s.ref, s.topic, s.submitted_at,"
            " (SELECT COUNT(*) FROM turns t WHERE t.submission_id=s.id) AS turn_count"
            " FROM submissions s WHERE s.student_id=? ORDER BY s.id DESC",
            (current_user()["id"],)).fetchall()
        return jsonify(submissions=[dict(r) for r in rows])

    @app.post("/api/student/submissions/<ref>/transcript")
    @require("student", api=True)
    def student_add_transcript(ref):
        db = get_db()
        row = get_submission_or_404(db, ref)
        if row is None or row["student_id"] != current_user()["id"]:
            return jsonify(error="Submission not found."), 404
        if db.execute("SELECT COUNT(*) FROM turns WHERE submission_id=?", (row["id"],)).fetchone()[0]:
            return jsonify(error="A transcript has already been supplied for this submission."), 409
        transcript = str(json_body().get("transcript", "")).replace("\r\n", "\n")
        if len(transcript) > MAX_TRANSCRIPT:
            return jsonify(error=f"Transcript exceeds {MAX_TRANSCRIPT:,} characters."), 400
        try:
            turns = analysis.parse_transcript(transcript)
        except ValueError as err:
            return jsonify(error=str(err)), 400
        assessment = llm_flags.assess(turns, allow_live=True, usage_ok=live_calls_ok(db))
        store_turns(db, row["id"], turns)
        save_llm_run(db, row["id"], assessment)
        store_flags(db, row["id"], row["final_text"], turns)
        db.execute("UPDATE submissions SET status='Not started' WHERE id=?", (row["id"],))
        db.commit()
        return jsonify(ref=ref, turns=len(turns))

    # ---- marker API ------------------------------------------------------ #
    @app.get("/api/submissions")
    @require("marker", api=True)
    def marker_queue():
        db = get_db()
        rows = db.execute(
            "SELECT s.ref, s.topic, s.status, s.submitted_at, u.username AS student,"
            " (SELECT COUNT(*) FROM turns t WHERE t.submission_id=s.id) AS turn_count,"
            " (SELECT COUNT(*) FROM flags f WHERE f.submission_id=s.id) AS flag_count"
            " FROM submissions s JOIN users u ON u.id=s.student_id ORDER BY s.id").fetchall()
        return jsonify(llm=llm_flags.public_status(), submissions=[dict(r) for r in rows])

    @app.get("/api/submissions/<ref>")
    @require("marker", api=True)
    def marker_record(ref):
        db = get_db()
        row = get_submission_or_404(db, ref)
        if row is None:
            return jsonify(error="Submission not found."), 404
        return jsonify(build_record(db, row))

    @app.put("/api/submissions/<ref>/flags/<flag_key>/decision")
    @require("marker", api=True)
    def marker_decision(ref, flag_key):
        db = get_db()
        row = get_submission_or_404(db, ref)
        flag = None if row is None else db.execute(
            "SELECT id FROM flags WHERE submission_id=? AND flag_key=?", (row["id"], flag_key)).fetchone()
        if flag is None:
            return jsonify(error="Flag not found."), 404
        data = json_body()
        decision, rationale = data.get("decision"), str(data.get("rationale", "")).strip()
        if decision not in DECISIONS or not rationale:
            return jsonify(error="Select a decision and enter a reason before saving."), 400
        if len(rationale) > MAX_RATIONALE:
            return jsonify(error=f"Reason exceeds {MAX_RATIONALE:,} characters."), 400
        db.execute(
            "INSERT INTO decisions (flag_id, marker_id, decision, rationale, decided_at) VALUES (?,?,?,?,?)"
            " ON CONFLICT(flag_id) DO UPDATE SET marker_id=excluded.marker_id, decision=excluded.decision,"
            " rationale=excluded.rationale, decided_at=excluded.decided_at",
            (flag["id"], current_user()["id"], decision, rationale, now()))
        db.execute("UPDATE submissions SET status='In progress' WHERE id=?", (row["id"],))
        db.commit()
        return jsonify(ok=True, status="In progress")

    @app.post("/api/submissions/<ref>/critique-check")
    @require("marker", api=True)
    def marker_critique_check(ref):
        """Run (or re-run) the critique check for one submission. Decisions on flags that remain are kept."""
        db = get_db()
        row = get_submission_or_404(db, ref)
        if row is None:
            return jsonify(error="Submission not found."), 404
        turns = load_turns(db, row["id"])
        assessment = llm_flags.assess(turns, allow_live=True, usage_ok=live_calls_ok(db))
        if assessment["status"] not in ("ok",):
            messages = {"off": "The critique check is switched off (LANE2_LLM_MODE=off).",
                        "not_applicable": "This submission has no student replies to assess.",
                        "not_run": "The critique check could not be run."}
            return jsonify(error=assessment["error"] or messages.get(assessment["status"], "The critique check could not be run."),
                           status=assessment["status"]), 400
        save_llm_run(db, row["id"], assessment)
        rebuild_keeping_decisions(db, row["id"], row["final_text"], turns)
        db.commit()
        return jsonify(build_record(db, get_submission_or_404(db, ref)))

    @app.put("/api/submissions/<ref>/note")
    @require("marker", api=True)
    def marker_note(ref):
        db = get_db()
        row = get_submission_or_404(db, ref)
        if row is None:
            return jsonify(error="Submission not found."), 404
        note = str(json_body().get("note", "")).strip()
        if len(note) > MAX_NOTE:
            return jsonify(error=f"Note exceeds {MAX_NOTE:,} characters."), 400
        db.execute("UPDATE submissions SET overall_note=?, status='In progress' WHERE id=?", (note, row["id"]))
        db.commit()
        return jsonify(ok=True, status="In progress")

    @app.post("/api/submissions/<ref>/complete")
    @require("marker", api=True)
    def marker_complete(ref):
        db = get_db()
        row = get_submission_or_404(db, ref)
        if row is None:
            return jsonify(error="Submission not found."), 404
        record = build_record(db, row)
        error = ""
        if not record["turns"]:
            error = "This review cannot be completed until the student supplies a transcript."
        elif not record["note"].strip():
            error = "Add and save an overall marker note first."
        elif any(f["id"] not in record["decisions"]
                 or record["decisions"][f["id"]]["decision"] == "Need more context"
                 for f in record["analysis"]["flags"]):
            error = "Resolve every flag. Items marked Need more context remain open."
        if error:
            return jsonify(error=error), 400
        db.execute("UPDATE submissions SET status='Reviewed' WHERE id=?", (row["id"],))
        db.commit()
        return jsonify(ok=True, status="Reviewed")

    @app.get("/api/submissions/<ref>/export")
    @require("marker", api=True)
    def marker_export(ref):
        """A readable PDF of one review: flags, marker decisions and notes, transcript and final text."""
        db = get_db()
        row = get_submission_or_404(db, ref)
        if row is None:
            return jsonify(error="Submission not found."), 404
        record = build_record(db, row)
        for d in db.execute(
                "SELECT f.flag_key, d.decided_at, u.username FROM decisions d"
                " JOIN flags f ON f.id=d.flag_id JOIN users u ON u.id=d.marker_id WHERE f.submission_id=?",
                (row["id"],)).fetchall():
            record["decisions"][d["flag_key"]].update(decided_at=d["decided_at"], decided_by=d["username"])
        pdf = pdf_report.build_review_pdf(record, now(), current_user()["username"])
        return Response(pdf, mimetype="application/pdf", headers={
            "Content-Disposition": f'inline; filename="{record["student"]}-{ref}-review.pdf"'})

    @app.get("/api/queue/export")
    @require("marker", api=True)
    def marker_queue_export():
        db = get_db()
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writerow(["Submission ID", "Topic", "Flags", "Evidence", "Status"])
        for row in db.execute("SELECT * FROM submissions ORDER BY id").fetchall():
            record = build_record(db, row)
            writer.writerow([csv_safe(x) for x in (
                record["id"], record["topic"], len(record["analysis"]["flags"]),
                record["analysis"]["coverage"], record["status"])])
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="lane2-review-queue.csv"'})


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("LANE2_PORT", "5000"))
    print(f"\nLane 2 Evidence Review is running. Open http://127.0.0.1:{port} in your browser.")
    print("Leave this window open while you use it. Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False)
