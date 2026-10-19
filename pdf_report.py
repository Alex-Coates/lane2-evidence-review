"""A readable PDF of one review, written without any extra packages.

The marker clicks "Export review" and gets a short report: who and what was reviewed, the flags
and the marker's decisions with their reasons, the overall note, the full AI transcript, the final
submission and the replies the critique check rated substantive. It uses the PDF standard fonts, so nothing needs installing.

Layout is simple on purpose: A4, one column, shaded blocks for transcript turns and evidence.
Text outside the Windows-1252 character set (for example emoji) is shown as "?".
"""
import zlib

PAGE_W, PAGE_H = 595.28, 841.89
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 54, 56, 62
CONTENT_W = PAGE_W - 2 * MARGIN_X

NAVY = (0.075, 0.161, 0.259)
INK = (0.078, 0.157, 0.231)
MUTED = (0.373, 0.447, 0.522)
TEAL = (0.0, 0.478, 0.408)
AMBER = (0.541, 0.31, 0.0)
MINT = (0.851, 0.953, 0.925)
GREY = (0.945, 0.961, 0.98)
LINE = (0.86, 0.89, 0.92)

# Helvetica character widths (units per 1000 of the font size) for characters 32 to 255 in Windows-1252.
_REGULAR = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 761,
    556, 761, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 761, 611, 761,
    761, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 761, 500, 667,
    278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
]

_BOLD = [
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 761,
    556, 761, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 761, 611, 761,
    761, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 761, 500, 667,
    278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278,
    611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556,
]


def clean(text):
    """Make text safe for the PDF standard fonts."""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    for old, new in (("\u2192", "->"), ("\u2190", "<-"), ("\u2194", "<->"), ("\u2713", "[x]"),
                     ("\u2717", "[ ]"), ("\u00a0", " "), ("\t", "    ")):
        text = text.replace(old, new)
    text = "".join(c for c in text if c == "\n" or ord(c) >= 32)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def text_width(text, size, bold=False):
    table = _BOLD if bold else _REGULAR
    total = 0
    for ch in text:
        code = ch.encode("cp1252", errors="replace")[0]
        total += table[code - 32] if 32 <= code <= 255 else 556
    return total * size / 1000.0


def wrap(text, width, size, bold=False):
    """Split text into lines that fit `width` points. Blank lines are kept."""
    lines = []
    for raw in clean(text).split("\n"):
        current = ""
        for word in raw.split(" "):
            trial = word if not current else current + " " + word
            if text_width(trial, size, bold) <= width:
                current = trial
                continue
            if current:
                lines.append(current)
                current = ""
            while text_width(word, size, bold) > width and len(word) > 1:  # break a very long word
                k = len(word)
                while k > 1 and text_width(word[:k], size, bold) > width:
                    k -= 1
                lines.append(word[:k])
                word = word[k:]
            current = word
        lines.append(current)
    return lines


def _escape(text):
    data = text.encode("cp1252", errors="replace")
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


class Doc:
    """Collects pages of drawing instructions and writes the PDF."""

    FONTS = {"regular": "F1", "bold": "F2", "italic": "F3"}

    def __init__(self, footer_text):
        self.footer_text = clean(footer_text)
        self.pages = []
        self.ops = []
        self.y = PAGE_H - MARGIN_TOP

    def new_page(self):
        self.pages.append(self.ops)
        self.ops = []
        self.y = PAGE_H - MARGIN_TOP

    def need(self, height):
        if self.y - height < MARGIN_BOTTOM:
            self.new_page()

    def _text(self, ops, x, baseline, text, size, style, color):
        r, g, b = color
        head = f"BT /{self.FONTS[style]} {size} Tf {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {baseline:.2f} Td (".encode("latin-1")
        ops.append(head + _escape(text) + b") Tj ET")

    def space(self, points):
        self.y -= points

    def para(self, text, size=10, style="regular", color=INK, indent=0, after=6, leading=None):
        leading = leading or size * 1.4
        for line in wrap(text, CONTENT_W - indent, size, style == "bold"):
            self.need(leading)
            self.y -= leading
            if line:
                self._text(self.ops, MARGIN_X + indent, self.y + leading * 0.27, line, size, style, color)
        self.y -= after

    def heading(self, text, size=14):
        self.need(size * 3)
        self.y -= size * 1.9
        self._text(self.ops, MARGIN_X, self.y + 2, clean(text), size, "bold", NAVY)
        self.y -= 6
        r, g, b = LINE
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG 0.8 w {MARGIN_X} {self.y:.2f} m {PAGE_W - MARGIN_X} {self.y:.2f} l S".encode())
        self.y -= 8

    def kv(self, label, value, label_width=96):
        for i, line in enumerate(wrap(value, CONTENT_W - label_width, 10)):
            self.need(14)
            self.y -= 14
            if i == 0:
                self._text(self.ops, MARGIN_X, self.y + 4, clean(label), 10, "bold", MUTED)
            if line:
                self._text(self.ops, MARGIN_X + label_width, self.y + 4, line, 10, "regular", INK)
        self.y -= 3

    def block(self, label, text, background=GREY, label_color=MUTED, after=8, size=9.5):
        """A shaded block with a small label. It can continue across a page break."""
        pad, leading = 8, size * 1.42
        self.need(pad * 2 + 30)
        lines = wrap(text, CONTENT_W - 2 * pad, size)
        state = {"ops": self.ops, "index": len(self.ops), "top": self.y}

        def close(bottom):
            r, g, b = background
            rect = f"{r:.3f} {g:.3f} {b:.3f} rg {MARGIN_X} {bottom:.2f} {CONTENT_W:.2f} {state['top'] - bottom:.2f} re f"
            state["ops"].insert(state["index"], rect.encode())

        self.y -= pad
        self.y -= 11
        self._text(self.ops, MARGIN_X + pad, self.y + 2, clean(label), 7.5, "bold", label_color)
        self.y -= 3
        for line in lines:
            if self.y - leading < MARGIN_BOTTOM:
                close(self.y - pad)
                self.new_page()
                state = {"ops": self.ops, "index": len(self.ops), "top": self.y}
                self.y -= pad
            self.y -= leading
            if line:
                self._text(self.ops, MARGIN_X + pad, self.y + leading * 0.27, line, size, "regular", INK)
        self.y -= pad
        close(self.y)
        self.y -= after

    def to_bytes(self, title):
        pages = self.pages + [self.ops]
        total = len(pages)
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None]
        for base in ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique"):
            objects.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>".encode())
        kids = []
        for number, ops in enumerate(pages, start=1):
            footer = []
            self._text(footer, MARGIN_X, 30, self.footer_text, 8, "regular", MUTED)
            label = f"Page {number} of {total}"
            self._text(footer, PAGE_W - MARGIN_X - text_width(label, 8), 30, label, 8, "regular", MUTED)
            data = zlib.compress(b"\n".join(ops + footer))
            page_id = len(objects) + 1
            content_id = len(objects) + 2
            kids.append(f"{page_id} 0 R")
            objects.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents {content_id} 0 R >>").encode())
            objects.append(f"<< /Length {len(data)} /Filter /FlateDecode >>\nstream\n".encode() + data + b"\nendstream")
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {total} >>".encode()
        info_id = len(objects) + 1
        objects.append(b"<< /Title (" + _escape(clean(title)) + b") /Creator (Lane 2 Evidence Review) >>")
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        for off in offsets:
            out += f"{off:010d} 00000 n \n".encode()
        out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
                f"startxref\n{xref}\n%%EOF\n").encode()
        return bytes(out)


# --------------------------------------------------------------------------- #
# The review report
# --------------------------------------------------------------------------- #
VERDICT_LABELS = {"blind_acceptance": "Blind acceptance", "generic": "Generic reply", "substantive": "Substantive reply"}


def stamp(iso):
    return iso[:16].replace("T", " ") + " UTC" if iso else ""


def build_review_pdf(record, exported_at, exported_by):
    """Build the PDF for one review. `record` is the dictionary the marker page uses."""
    analysis = record["analysis"]
    flags, decisions, check = analysis["flags"], record["decisions"], record["critique_check"]
    turns = record["turns"]
    doc = Doc(f"Lane 2 Evidence Review  |  {record['student']}  |  {record['topic']}")

    # ---- title ----
    doc.para("LANE 2 EVIDENCE REVIEW", size=9, style="bold", color=TEAL, after=2)
    doc.para("Review report", size=24, style="bold", color=NAVY, after=8, leading=30)
    doc.kv("Student", record["student"])
    doc.kv("Topic", record["topic"])
    doc.kv("Reference", record["id"])
    doc.kv("Status", record["status"])
    doc.kv("Submitted", stamp(record["submitted_at"]))
    doc.kv("Exported", f"{stamp(exported_at)} by {exported_by}")
    doc.space(6)
    doc.block("NOTE", "Review flags are reasons to look closer, not conclusions. No grade is assigned. "
                      "The marker makes every decision recorded in this report.", background=MINT, label_color=TEAL)

    # ---- summary ----
    decided = [f for f in flags if f["id"] in decisions]
    counts = {}
    for d in decisions.values():
        counts[d["decision"]] = counts.get(d["decision"], 0) + 1
    overlap_count = sum(1 for f in flags if f["origin"] == "rule")
    doc.heading("Summary")
    doc.kv("Review flags", f"{len(flags)} ({len(flags) - overlap_count} from the critique check, {overlap_count} from the wording comparison)")
    if flags:
        detail = ": " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) if counts else ""
        doc.kv("Decisions", f"{len(decided)} of {len(flags)} flags decided{detail}")
    else:
        doc.kv("Decisions", "No flags to decide")
    if turns:
        c = record["contribution"]
        doc.kv("Wording overlap", f"{c['ai_percent']}% of the final submission's words ({c['ai_words']} of {c['words']}) sit inside "
                                  "five-word phrases that also appear in an AI turn. This measures matching wording, not who wrote the text.")
    else:
        doc.kv("Transcript", "Not supplied. The final submission could not be compared with AI output.")
    how = {"live": "live", "cached": "saved result", "mock": "simulated stand-in (not a language model)"}.get(check["mode"], "")
    if check["status"] == "ok":
        model = f", model {check['model']}" if check["model"] and check["mode"] != "mock" else ""
        doc.kv("Critique check", f"{how}{model}, rubric v{check['rubric_version']}, {len(check['assessments'])} replies rated")
    elif check["status"] == "not_applicable":
        doc.kv("Critique check", "No student replies to rate.")
    elif check["status"] == "off":
        doc.kv("Critique check", "Switched off.")
    elif check["status"] == "not_run" and not check["error"]:
        doc.kv("Critique check", "Not run.")
    else:
        doc.kv("Critique check", "Not available" + (f": {check['error']}" if check["error"] else "."))

    # ---- marker's overall note ----
    doc.heading("Marker's overall note")
    has_note = bool(record["note"].strip())
    doc.para(record["note"].strip() if has_note else "No overall note has been saved.", color=INK if has_note else MUTED)

    # ---- flags and decisions ----
    doc.heading("Flags and marker decisions")
    if not turns:
        doc.para("No transcript was supplied, so there is nothing to compare the final submission with.", color=MUTED)
    elif not flags:
        doc.para("No flags were raised by the current checks. This does not prove critical engagement.", color=MUTED)
    for i, f in enumerate(flags, start=1):
        doc.need(120)
        if f["type"] == "Text overlap":
            title = f"{i}. Text overlap, {round(f['score'] * 100)}% phrase similarity"
            left = (f"AI OUTPUT  |  TURN {f['turn'] + 1}", f["source"])
            right = (f"FINAL SUBMISSION  |  PARAGRAPH {f['paragraph'] + 1}", f["target"])
        else:
            title = f"{i}. Critique quality, {VERDICT_LABELS.get(f['verdict'], '')}"
            title += " (simulated check)" if check["mode"] == "mock" else " (LLM-assisted)"
            left = (f"AI OUTPUT  |  TURN {f['turn']}", f["source"])
            right = (f"STUDENT REPLY  |  TURN {f['turn'] + 1}", f["target"])
        doc.para(title, size=11, style="bold", color=NAVY, after=2)
        doc.para(f["reason"], size=9.5, color=MUTED, after=5)
        doc.block(*left)
        doc.block(*right, after=5)
        if f.get("quote"):
            doc.para(f"Quoted from the reply: \u201c{f['quote']}\u201d", size=9.5, style="italic", color=INK, after=5)
        d = decisions.get(f["id"])
        if d:
            colour = {"Accept flag": TEAL, "Dismiss flag": MUTED}.get(d["decision"], AMBER)
            doc.para(f"Marker decision: {d['decision']}", size=10.5, style="bold", color=colour, after=2)
            doc.para(f"Reason: {d['rationale']}", size=10, after=2)
            meta = []
            if d.get("decided_by"):
                meta.append(f"Recorded by {d['decided_by']}")
            if d.get("decided_at"):
                meta.append(f"on {stamp(d['decided_at'])}")
            if meta:
                doc.para(" ".join(meta), size=8.5, color=MUTED, after=10)
            else:
                doc.space(6)
        else:
            doc.para("Marker decision: not yet recorded", size=10.5, style="bold", color=AMBER, after=12)

    # ---- transcript ----
    doc.heading("Full interaction history")
    if turns:
        flagged = {f["turn"] for f in flags}
        doc.para("All supplied turns, in order. Turns that are part of a flag are marked.", size=9, color=MUTED, after=6)
        for i, t in enumerate(turns):
            mark = "   (part of a flag)" if i in flagged else ""
            doc.block(f"{t['role'].upper()}  |  TURN {i + 1}{mark}", t["text"],
                      background=MINT if t["role"] == "Student" else GREY,
                      label_color=TEAL if t["role"] == "Student" else MUTED, after=6)
    else:
        doc.para("No transcript supplied.", color=MUTED)

    # ---- final submission ----
    doc.heading("Final submission")
    for i, p in enumerate(analysis["paragraphs"], start=1):
        doc.block(f"PARAGRAPH {i}", p, after=6)

    # ---- replies rated substantive ----
    doc.heading("Replies rated substantive")
    if check["status"] != "ok":
        doc.para("The critique check did not rate this submission's replies" + (f": {check['error']}" if check["error"] else "."), color=MUTED)
    else:
        good = [a for a in check["assessments"] if a["verdict"] == "substantive"]
        if good:
            doc.para("Replies the critique check rated as engaging with specific content of the AI answer. "
                     "Read them alongside any flags.", size=9, color=MUTED, after=6)
            for a in good:
                doc.block(f"STUDENT  |  TURN {a['turn']}", turns[a["index"]]["text"], background=MINT, label_color=TEAL, after=2)
                doc.para(a["reason"], size=9, style="italic", color=MUTED, after=8)
        else:
            doc.para("No replies were rated substantive.", color=MUTED)

    # ---- method note ----
    doc.heading("How these flags were produced")
    doc.para("An OpenAI model reads every student reply that follows an AI answer and rates it as substantive, generic or "
             "blind acceptance. Generic replies and blind acceptance become flags, each with a quote that is checked against the "
             "student's own text. A separate wording comparison flags paragraphs of the final submission that closely match an AI "
             "turn. These are prompts for a human marker. They do not establish authorship, engagement quality or academic misconduct.",
             size=9.5, color=MUTED)
    return doc.to_bytes(f"Review report {record['student']} {record['id']}")
