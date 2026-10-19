"""Wording comparison for Lane 2 Evidence Review.

This module holds the one check that is NOT done by the OpenAI model: comparing the final
submission with the AI turns. Everything about how the student responded to the AI (brief
acceptance, generic requests, substantive critique) is judged by the critique check in
llm_flags.py.

Text overlap
    Each paragraph of the final submission is compared with every AI turn.
    Text is lowercased, punctuation removed, and split into consecutive
    five-word phrases. Similarity is the Jaccard index of the two phrase sets:
        shared phrases / distinct phrases in either text
    The best-matching AI turn is flagged if its score reaches the standard review
    threshold. The flag is a prompt for a marker to look closer, never a grade.

Wording overlap (contribution)
    The share of the final submission's words that sit inside five-word phrases which
    also appear in an AI turn, used for the bar and highlighting on the marker page.
"""
import re

DEFAULT_THRESHOLD = 0.65
TURN_LINE = re.compile(r"^(Student|AI):\s*(.*)$", re.IGNORECASE)


def words(text):
    """Lowercase and keep only letters and digits, as a list of words."""
    return re.findall(r"[a-z0-9]+", text.lower())


def phrases(text, size=5):
    """The set of consecutive `size`-word phrases in `text`."""
    w = words(text)
    return {" ".join(w[i : i + size]) for i in range(len(w) - size + 1)}


def similarity(a, b):
    """Jaccard similarity of the five-word phrase sets of two texts (0 to 1)."""
    x, y = phrases(a), phrases(b)
    if not x or not y:
        return 0.0
    shared = len(x & y)
    return shared / (len(x) + len(y) - shared)


def parse_transcript(text):
    """Turn pasted 'Student: ... / AI: ...' text into a list of turns.

    The turns must alternate between Student and AI, because the checks compare each student
    reply with the AI answer that came directly before it.

    Raises ValueError with a message the user can act on if the text is invalid.
    """
    turns = []
    for line in re.split(r"\r?\n", text):
        m = TURN_LINE.match(line)
        if m:
            role = "AI" if m.group(1).lower() == "ai" else "Student"
            turns.append({"role": role, "text": m.group(2)})
        elif line.strip():
            if not turns:
                raise ValueError("Start each turn with Student: or AI:.")
            turns[-1]["text"] += "\n" + line
    if not turns or any(not t["text"].strip() for t in turns):
        raise ValueError("Each labelled turn needs text.")
    roles = {t["role"] for t in turns}
    if roles != {"AI", "Student"}:
        raise ValueError("Include at least one Student: turn and one AI: turn.")
    for i in range(1, len(turns)):
        if turns[i]["role"] == turns[i - 1]["role"]:
            raise ValueError(
                f"Turns must alternate between Student: and AI:. Turns {i} and {i + 1} are both {turns[i]['role']}:.")
    return turns


def split_paragraphs(final_text):
    return [p for p in re.split(r"\n\s*\n", final_text) if p.strip()]


def structure(final_text, turns):
    """Everything about a submission that does not depend on the threshold."""
    ai_turns = [t for t in turns if t["role"] == "AI"]
    return {
        "coverage": "Transcript supplied" if ai_turns else "Missing transcript",
        "paragraphs": split_paragraphs(final_text),
    }


def analyze(final_text, turns, threshold=DEFAULT_THRESHOLD):
    """Compare each paragraph of the final submission with the AI turns and return the flags."""
    result = structure(final_text, turns)
    flags = []
    ai_indexes = [i for i, t in enumerate(turns) if t["role"] == "AI"]
    if not ai_indexes:
        result["flags"] = flags
        return result

    for p_index, paragraph in enumerate(result["paragraphs"]):
        best_turn, best_score = None, None
        for i in ai_indexes:
            score = similarity(paragraph, turns[i]["text"])
            if best_score is None or score > best_score:
                best_turn, best_score = i, score
        if best_score is not None and best_score >= threshold:
            flags.append(
                {
                    "key": f"overlap-{p_index}",
                    "type": "Text overlap",
                    "paragraph": p_index,
                    "turn": best_turn,
                    "score": best_score,
                    "source": turns[best_turn]["text"],
                    "target": paragraph,
                    "reason": (
                        f"The paragraph matches AI turn {best_turn + 1} under the five-word "
                        "phrase rule. Read the surrounding interaction before interpreting this flag."
                    ),
                }
            )

    result["flags"] = flags
    return result


def contribution(final_text, turns):
    """Wording overlap between the final submission and the AI turns.

    A word counts as "AI-matching" if it sits inside a five-word phrase that also
    appears in at least one AI turn. This measures wording overlap only. It does not
    show who wrote the text, and paraphrased AI text is not detected.

    Returns the overall percentage and, for each paragraph, a list of segments
    ({"text": ..., "ai": True/False}) so the page can highlight the matching words.
    """
    ai_phrases = set()
    for t in turns:
        if t["role"] == "AI":
            ai_phrases |= phrases(t["text"])
    paragraphs, covered_total, word_total = [], 0, 0
    for p in split_paragraphs(final_text):
        tokens = [(m.group(0).lower(), m.start(), m.end()) for m in re.finditer(r"[A-Za-z0-9]+", p)]
        covered = [False] * len(tokens)
        for i in range(len(tokens) - 4):
            if " ".join(t[0] for t in tokens[i : i + 5]) in ai_phrases:
                for j in range(i, i + 5):
                    covered[j] = True
        segments, pos, i = [], 0, 0
        while i < len(tokens):
            if covered[i]:
                j = i
                while j + 1 < len(tokens) and covered[j + 1]:
                    j += 1
                start, end = tokens[i][1], tokens[j][2]
                if start > pos:
                    segments.append({"text": p[pos:start], "ai": False})
                segments.append({"text": p[start:end], "ai": True})
                pos, i = end, j + 1
            else:
                i += 1
        if pos < len(p):
            segments.append({"text": p[pos:], "ai": False})
        paragraphs.append(segments)
        covered_total += sum(covered)
        word_total += len(tokens)
    ai_percent = int(100 * covered_total / word_total + 0.5) if word_total else 0
    return {
        "ai_percent": ai_percent,
        "other_percent": 100 - ai_percent if word_total else 0,
        "words": word_total,
        "ai_words": covered_total,
        "paragraphs": paragraphs,
    }
