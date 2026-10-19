"""Tests for the PDF review report (pdf_report.py)."""
import os
import re
import sys
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LANE2_LLM_MODE"] = "off"
os.environ.pop("OPENAI_API_KEY", None)

import pdf_report  # noqa: E402


def pdf_text(data):
    """All the text drawn on every page, one string (for checking what a reader would see)."""
    out = []
    for m in re.finditer(rb"stream\n(.*?)\nendstream", data, re.S):
        for line in zlib.decompress(m.group(1)).split(b"\n"):
            t = re.search(rb"Td \((.*)\) Tj ET$", line)
            if t:
                raw = re.sub(rb"\\([\\()])", rb"\1", t.group(1))
                out.append(raw.decode("cp1252"))
    return "\n".join(out)


def sample_record(turns=None, note="", decisions=None, paragraphs=None):
    turns = turns if turns is not None else [{"role": "Student", "text": "Question?"}, {"role": "AI", "text": "Answer."},
                                             {"role": "Student", "text": "Thanks."}]
    return {
        "id": "SUB-001", "student": "aiye355", "topic": "Sample (topic) \\ test", "status": "Not started", "note": note,
        "submitted_at": "2026-10-15T01:02:03+00:00", "turns": turns, "decisions": decisions or {},
        "analysis": {"flags": [], "coverage": "Transcript supplied", "paragraphs": paragraphs or ["Some final text."]},
        "critique_check": {"status": "off", "mode": "none", "model": None, "rubric_version": "1.0", "error": None,
                           "rejected": 0, "assessments": []},
        "contribution": {"ai_percent": 0, "other_percent": 100, "words": 3, "ai_words": 0, "paragraphs": [[{"text": "Some final text.", "ai": False}]]},
    }


class PdfStructureTests(unittest.TestCase):
    def assert_valid(self, data):
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        start = int(re.search(rb"startxref\n(\d+)", data).group(1))
        self.assertTrue(data[start:].startswith(b"xref"))
        count = int(re.search(rb"/Size (\d+)", data).group(1))
        offsets = re.findall(rb"(\d{10}) 00000 n", data[start:])
        self.assertEqual(len(offsets), count - 1)
        for number, off in enumerate(offsets, start=1):
            self.assertTrue(data[int(off):].startswith(f"{number} 0 obj".encode()), number)
        pages = len(re.findall(rb"/Type /Page /", data))
        self.assertEqual(pages, int(re.search(rb"/Count (\d+)", data).group(1)))
        return pages

    def test_small_report_is_valid_and_has_the_expected_content(self):
        data = pdf_report.build_review_pdf(sample_record(note="Marker note here."), "2026-10-15T03:00:00+00:00", "marker1")
        pages = self.assert_valid(data)
        text = pdf_text(data)
        for expected in ("Review report", "Student", "aiye355", "Exported", "2026-10-15 03:00 UTC by marker1", "Marker note here.",
                         "STUDENT  |  TURN 1", "AI  |  TURN 2", f"Page {pages} of {pages}", "No flags were raised by the current checks."):
            self.assertIn(expected, text)

    def test_special_characters_are_escaped_and_do_not_break_the_file(self):
        data = pdf_report.build_review_pdf(sample_record(), "2026-10-15T03:00:00+00:00", "marker1")
        self.assert_valid(data)
        self.assertIn("Sample (topic) \\ test", pdf_text(data))

    def test_unsupported_characters_and_curly_quotes(self):
        record = sample_record(note="Curly \u2019quotes\u2019, a dash \u2013, an arrow \u2192 and an emoji \U0001F600.")
        text = pdf_text(pdf_report.build_review_pdf(record, "2026-10-15T03:00:00+00:00", "marker1"))
        self.assertIn("Curly \u2019quotes\u2019, a dash \u2013, an arrow -> and an emoji ?.", text)

    def test_long_transcripts_continue_across_pages(self):
        turns = []
        for i in range(30):
            turns.append({"role": "Student", "text": f"Question {i}? " + "words " * 40})
            turns.append({"role": "AI", "text": f"Answer {i}. " + "detail " * 80})
        data = pdf_report.build_review_pdf(sample_record(turns=turns), "2026-10-15T03:00:00+00:00", "marker1")
        pages = self.assert_valid(data)
        self.assertGreater(pages, 3)
        text = pdf_text(data)
        self.assertIn("AI  |  TURN 60", text)
        self.assertIn(f"Page {pages} of {pages}", text)

    def test_one_huge_block_splits_over_a_page_break(self):
        data = pdf_report.build_review_pdf(sample_record(note="x " * 5000), "2026-10-15T03:00:00+00:00", "marker1")
        self.assertGreater(self.assert_valid(data), 1)

    def test_very_long_unbroken_word_is_wrapped(self):
        lines = pdf_report.wrap("a" * 400, 200, 10)
        self.assertGreater(len(lines), 2)
        self.assertTrue(all(pdf_report.text_width(line, 10) <= 200 for line in lines))

    def test_missing_transcript_report(self):
        record = sample_record(turns=[])
        record["analysis"]["coverage"] = "Missing transcript"
        text = pdf_text(pdf_report.build_review_pdf(record, "2026-10-15T03:00:00+00:00", "marker1"))
        self.assertIn("No transcript was supplied", text)
        self.assertIn("Not supplied.", text)

    def test_decisions_and_unrecorded_decisions_are_shown(self):
        record = sample_record(turns=[{"role": "Student", "text": "Q?"}, {"role": "AI", "text": "A."}, {"role": "Student", "text": "Thanks."},
                                      {"role": "AI", "text": "B."}, {"role": "Student", "text": "Good answer."}],
                               decisions={"critique-2": {"decision": "Dismiss flag", "rationale": "Polite reply.",
                                                         "decided_by": "marker1", "decided_at": "2026-10-15T02:00:00+00:00"}})
        record["critique_check"].update(status="ok", mode="live", model="gpt-5.4-mini", assessments=[
            {"turn": 3, "index": 2, "verdict": "blind_acceptance", "quote": "Thanks.", "reason": "Only thanks."},
            {"turn": 5, "index": 4, "verdict": "blind_acceptance", "quote": "Good answer.", "reason": "Only approval."}])
        record["analysis"]["flags"] = [
            {"id": "critique-2", "type": "Critique quality", "paragraph": None, "turn": 2, "score": None, "source": "A.", "target": "Thanks.",
             "reason": "Only thanks.", "origin": "llm", "verdict": "blind_acceptance", "quote": "Thanks."},
            {"id": "critique-4", "type": "Critique quality", "paragraph": None, "turn": 4, "score": None, "source": "B.", "target": "Good answer.",
             "reason": "Only approval.", "origin": "llm", "verdict": "blind_acceptance", "quote": "Good answer."}]
        text = pdf_text(pdf_report.build_review_pdf(record, "2026-10-15T03:00:00+00:00", "marker1"))
        for expected in ("1. Critique quality, Blind acceptance (LLM-assisted)", "Marker decision: Dismiss flag", "Reason: Polite reply.",
                         "Recorded by marker1 on 2026-10-15 02:00 UTC", "Marker decision: not yet recorded",
                         "1 of 2 flags decided: 1 Dismiss flag", "2 from the critique check, 0 from the wording comparison",
                         "Quoted from the reply: \u201cThanks.\u201d", "gpt-5.4-mini"):
            self.assertIn(expected, text)

    def test_replies_rated_substantive_are_listed_with_the_models_reason(self):
        record = sample_record(turns=[{"role": "Student", "text": "Q?"}, {"role": "AI", "text": "A."},
                                      {"role": "Student", "text": "That is incorrect because the figure is wrong."}])
        record["critique_check"].update(status="ok", mode="cached", model="gpt-5.4-mini", assessments=[
            {"turn": 3, "index": 2, "verdict": "substantive", "quote": "That is incorrect", "reason": "Challenges a specific figure."}])
        text = pdf_text(pdf_report.build_review_pdf(record, "2026-10-15T03:00:00+00:00", "marker1"))
        self.assertIn("Replies rated substantive", text)
        self.assertIn("STUDENT  |  TURN 3", text)
        self.assertIn("That is incorrect because the figure is wrong.", text)
        self.assertIn("Challenges a specific figure.", text)

    def test_substantive_section_explains_when_the_check_did_not_run(self):
        text = pdf_text(pdf_report.build_review_pdf(sample_record(), "2026-10-15T03:00:00+00:00", "marker1"))
        self.assertIn("The critique check did not rate this submission's replies.", text)
        self.assertNotIn("Reasoning keywords", text)


if __name__ == "__main__":
    unittest.main()
