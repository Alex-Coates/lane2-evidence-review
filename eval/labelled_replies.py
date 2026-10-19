"""Labelled student replies for comparing the rule-based flags with the OpenAI critique check.

IMPORTANT FOR THE TEAM: these labels are a DRAFT written by the AI tool. The team must read
them, correct any label it disagrees with, and treat its own labels as the ground truth. Each
item is (AI answer, student reply, label, note). Labels:
    S  substantive       engages with specific content of the AI answer
    G  generic           keeps the conversation going without evaluating the answer
    B  blind acceptance  accepts, thanks or approves without evaluating
All text is fictional.
"""

AI_SOLAR = "Every school should install a battery because batteries always make solar power more economical."
AI_BUS = "Better bus services can improve access to employment and education. Outcomes depend on frequency, reliability and affordability."
AI_WATER = "Reusing suitably treated wastewater can support irrigation and industrial demand, with monitoring and maintenance planned."
AI_GRANT = "Community solar grants can reduce a school's electricity costs by generating power during daylight hours."
AI_FUND = "Index funds outperform every active fund, so investors should never choose an active fund."
AI_SURVEY = "Use a five-point Likert scale because it gives you interval data that you can average."

ITEMS = [
    # ---- substantive (12) ----
    (AI_SOLAR, "That payback claim seems too certain. What assumptions about battery cost and electricity prices does it rely on?", "S", ""),
    (AI_BUS, "Frequency matters, but you have not said how affordability was measured. Can you point to a study that tested it?", "S", ""),
    (AI_WATER, "I do not think that is complete. Treatment quality has to match the end use, so please add what monitoring would be needed for irrigation.", "S", ""),
    (AI_FUND, "Every active fund is wrong, surely. Rewrite it to say most underperform after fees and tell me where that comes from.", "S", ""),
    (AI_SURVEY, "Likert data is usually treated as ordinal, so I am not sure the interval claim holds for my survey. What is the assumption?", "S", ""),
    (AI_GRANT, "Thanks, but that ignores schools with shaded roofs. Revise it for a school with no spare roof space.", "S", "thanks plus a specific concern"),
    (AI_SOLAR, "That assumption is incorrect. A school uses much of its power during the day. What evidence supports a battery at every site?", "S", ""),
    (AI_BUS, "Free for whom? That ignores funding.", "S", "short but specific"),
    (AI_FUND, "Please check the claim about never choosing an active fund. The 2020 report I read said results differ by market.", "S", ""),
    (AI_WATER, "However, I need to verify the evidence for monitoring costs. The wording is useful but does not show our plant can afford it.", "S", ""),
    (AI_SURVEY, "Averaging is only valid if the gaps between points are equal, and my respondents may not see them that way. Offer an alternative.", "S", ""),
    (AI_GRANT, "Where does the daylight claim come from? Our grant rules say storage must be included.", "S", ""),
    # ---- generic (12) ----
    (AI_GRANT, "Can you expand on that?", "G", ""),
    (AI_BUS, "Make it longer.", "G", ""),
    (AI_WATER, "Continue.", "G", ""),
    (AI_SOLAR, "Give me more detail please.", "G", ""),
    (AI_FUND, "Rewrite it in a more formal tone.", "G", "formatting request with no reason"),
    (AI_SURVEY, "Add some more bullet points.", "G", ""),
    (AI_GRANT, "Go on.", "G", ""),
    (AI_BUS, "Can you give me another version?", "G", ""),
    (AI_WATER, "Summarise that in one paragraph.", "G", ""),
    (AI_SOLAR, "Make it sound better.", "G", ""),
    (AI_FUND, "Explain more about the second point.", "G", "borderline: names a point but does not evaluate it"),
    (AI_SURVEY, "Translate that into simple English.", "G", ""),
    # ---- blind acceptance (12) ----
    (AI_GRANT, "Thanks!", "B", "also caught by the rule list"),
    (AI_BUS, "Looks good to me.", "B", ""),
    (AI_WATER, "Great, that makes sense.", "B", ""),
    (AI_SOLAR, "Perfect, thank you so much.", "B", ""),
    (AI_FUND, "I agree.", "B", "also caught by the rule list"),
    (AI_SURVEY, "Good answer.", "B", "also caught by the rule list"),
    (AI_GRANT, "ok", "B", ""),
    (AI_BUS, "Yes, that is exactly what I needed.", "B", ""),
    (AI_WATER, "Brilliant, I will use that.", "B", ""),
    (AI_SOLAR, "That sounds right.", "B", ""),
    (AI_FUND, "Thank you, that is very helpful and clear.", "B", "also caught by the rule list"),
    (AI_SURVEY, "Nice one, copying that into my report.", "B", ""),
]
