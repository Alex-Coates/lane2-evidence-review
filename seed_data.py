"""Synthetic data for Lane 2 Evidence Review.

Everything here is fictional and was written by the team to exercise the two flag
rules, including edge cases and known limitations. Test accounts are for local
testing only: never reuse these passwords anywhere else.
"""

# Bump this whenever the seed data or accounts change. If an existing database was
# created with a different version, the app backs it up and builds a fresh one.
SEED_VERSION = "2.4"

SEED_USERS = [
    # (username, password, role, display name)
    ("Ruhi", None, "marker", "Ruhi"),
    ("aiye355", "student-pass-1", "student", "aiye355"),
    ("hluo185", "student-pass-2", "student", "hluo185"),
    ("acoa536", "student-pass-3", "student", "acoa536"),
    ("hcoo867", "student-pass-4", "student", "hcoo867"),
    # Fictional submitters who appear in the review queue but have no login
    # (password None means nobody can sign in as them).
    ("rnav609", None, "student", "rnav609"),
    ("kugn020", None, "student", "kugn020"),
]

SEED_SUBMISSIONS = [{'ref': 'SYN-101',
  'student': 'aiye355',
  'topic': 'Community energy grants',
  'final_text': 'Solar panels can reduce a school’s electricity costs by generating power during daylight '
                'hours. Battery storage can shift surplus generation into the evening and provide backup '
                'during interruptions. However, installation costs and site suitability must be assessed '
                'before funding is approved.',
  'turns': [{'role': 'Student', 'text': 'Explain community solar grants for schools.'},
            {'role': 'AI',
             'text': 'Solar panels can reduce a school’s electricity costs by generating power during '
                     'daylight hours. Battery storage can shift surplus generation into the evening and '
                     'provide backup during interruptions. However, installation costs and site suitability '
                     'must be assessed before funding is approved.'},
            {'role': 'Student', 'text': 'Good answer.'}],
  'submitted_at': '2026-09-21T01:12:00+00:00'},
 {'ref': 'SYN-102',
  'student': 'hluo185',
  'topic': 'Evaluating a solar proposal',
  'final_text': 'Schools should first compare daytime electricity demand with expected solar output. A '
                'battery may be unnecessary where most generation is consumed during teaching hours. Funding '
                'decisions should use site-specific costs and a maintenance plan.',
  'turns': [{'role': 'Student', 'text': 'Should every school receive a battery with solar panels?'},
            {'role': 'AI',
             'text': 'Every school should install a battery because batteries always make solar power more '
                     'economical.'},
            {'role': 'Student',
             'text': 'That assumption is incorrect. A school uses much of its power during the day. What '
                     'evidence supports a battery at every site? Compare its additional cost with savings.'},
            {'role': 'AI',
             'text': 'A site assessment should compare battery costs, demand patterns and resilience '
                     'needs.'}],
  'submitted_at': '2026-09-21T03:40:00+00:00'},
 {'ref': 'SYN-103',
  'student': 'hcoo867',
  'topic': 'Water infrastructure',
  'final_text': 'Pipe renewal programmes reduce water losses by replacing ageing infrastructure and '
                'improving the reliability of local water networks. Smart meters help operators identify '
                'unusual consumption patterns and prioritise inspections where leakage is suspected.',
  'turns': [],
  'submitted_at': '2026-09-22T00:05:00+00:00'},
 {'ref': 'SYN-104',
  'student': 'acoa536',
  'topic': 'Checking a transport claim',
  'final_text': 'Better bus services can improve access to employment and education. Outcomes depend on '
                'frequency, reliability, route coverage and affordability. A transport policy should '
                'evaluate these factors before projecting changes in ridership.',
  'turns': [{'role': 'Student', 'text': 'Explain access benefits of buses.'},
            {'role': 'AI',
             'text': 'Better bus services can improve access to employment and education. Outcomes depend on '
                     'frequency, reliability, route coverage and affordability. A transport policy should '
                     'evaluate these factors before projecting changes in ridership.'},
            {'role': 'Student', 'text': 'I agree.'},
            {'role': 'AI',
             'text': 'Noted. If it would help, I can suggest ways to measure whether ridership changes after a new '
                     'route is introduced.'},
            {'role': 'Student',
             'text': 'However, I need to verify the evidence for ridership changes. The wording is useful, '
                     'but does not establish that our proposed route will achieve these benefits.'}],
  'submitted_at': '2026-09-22T02:30:00+00:00'},
 {'ref': 'SYN-105',
  'student': 'rnav609',
  'topic': 'Wastewater reuse',
  'final_text': 'Wastewater reuse can reduce demand on drinking-water supplies when treated water is '
                'suitable for its intended use. Monitoring, maintenance and clear operational '
                'responsibilities are necessary to manage the programme.',
  'turns': [{'role': 'Student', 'text': 'Give me an overview of wastewater reuse.'},
            {'role': 'AI',
             'text': 'Reusing suitably treated wastewater can support irrigation and industrial demand. '
                     'Treatment quality should be assessed against the proposed end use, with monitoring and '
                     'maintenance planned.'},
            {'role': 'Student', 'text': 'Thanks!'}],
  'submitted_at': '2026-09-23T04:18:00+00:00'},
 {'ref': 'SYN-106',
  'student': 'kugn020',
  'topic': 'Human review and uncertainty',
  'final_text': 'A dashboard should help a marker find relevant evidence while keeping the final assessment '
                'decision with the educator. Similar wording may be legitimate, and missing interaction '
                'records can limit what the marker can conclude.',
  'turns': [{'role': 'Student', 'text': 'Suggest a fair approach to reviewing AI interactions.'},
            {'role': 'AI',
             'text': 'Give every student an automatic engagement score based on how many prompts they '
                     'submitted.'},
            {'role': 'Student',
             'text': 'Prompt count is not enough because it does not show whether the student evaluated the '
                     'response. Show the underlying evidence and let the marker decide.'}],
  'submitted_at': '2026-09-23T21:50:00+00:00'},
 {'ref': 'SYN-107',
  'student': 'aiye355',
  'topic': 'Urban tree planting',
  'final_text': 'Stormwater benefits depend on soil type, tree spacing and the condition of nearby drains, '
                'so councils should measure these locally before estimating savings.\n'
                '\n'
                'Urban tree planting lowers summer street temperatures by providing shade and releasing '
                'moisture through leaves. Street trees also reduce stormwater runoff by intercepting '
                'rainfall and letting water soak into the ground. Councils should select species suited to '
                'local soil and plan long-term upkeep.\n'
                '\n'
                'Urban tree planting lowers summer street temperatures through shade and by releasing '
                'moisture through leaves. Street trees also reduce stormwater runoff by catching rainfall '
                'and allowing water to soak into the ground. Councils should select species suited to local '
                'soil and plan long-term maintenance.\n'
                '\n'
                'In my own view, the strongest case for planting is shade on footpaths used by children '
                'walking to school, since that benefit is easy to observe and does not rely on drainage '
                'data.',
  'turns': [{'role': 'Student', 'text': 'Explain the benefits of planting trees along city streets.'},
            {'role': 'AI',
             'text': 'Urban tree planting lowers summer street temperatures by providing shade and releasing '
                     'moisture through leaves. Street trees also reduce stormwater runoff by intercepting '
                     'rainfall and allowing water to soak into the ground. Councils should select species '
                     'suited to local soil and plan long-term maintenance.'},
            {'role': 'Student', 'text': 'Which of these claims depends most on local conditions?'},
            {'role': 'AI',
             'text': 'Stormwater benefits depend on soil type, tree spacing and the condition of nearby '
                     'drains, so councils should measure these locally before estimating savings.'}],
  'submitted_at': '2026-09-24T01:02:00+00:00'},
 {'ref': 'SYN-108',
  'student': 'hluo185',
  'topic': 'Housing affordability claim',
  'final_text': 'Rent growth alone does not show a housing shortage. A fair assessment needs household '
                'incomes, the number of new dwellings consented and vacancy rates in the same period.\n'
                '\n'
                'The claim that building more homes always lowers rents is too strong. Local planning rules '
                'and construction costs can limit how quickly new supply reaches the market.',
  'turns': [{'role': 'Student', 'text': 'Is rising rent proof of a housing shortage?'},
            {'role': 'AI',
             'text': 'Yes. Rising rents are conclusive proof that a city has a housing shortage and building '
                     'more homes will always reduce them.'},
            {'role': 'Student',
             'text': 'That seems too certain. Rents also rise because incomes or interest rates change. What '
                     'evidence would separate those causes?'},
            {'role': 'AI',
             'text': 'You could compare rent growth with income growth, vacancy rates and the number of new '
                     'dwellings consented over the same period.'},
            {'role': 'Student',
             'text': 'However, I still do not accept that building more homes always lowers rents, because '
                     'planning rules and costs may slow new supply. Please correct that claim.'},
            {'role': 'AI',
             'text': 'That is a fair correction. Additional supply can moderate rents, but the effect '
                     'depends on local planning rules, construction costs and demand.'}],
  'submitted_at': '2026-09-24T05:45:00+00:00'},
 {'ref': 'SYN-109',
  'student': 'kugn020',
  'topic': 'Public library opening hours',
  'final_text': 'Longer evening hours would let working people and students use the library after their '
                'commitments end. The council should compare usage during extended hours against staffing '
                'costs before committing funds.',
  'turns': [{'role': 'Student', 'text': 'Should libraries open later in the evening?'},
            {'role': 'AI',
             'text': 'Later opening can help people who work or study during the day, but it increases '
                     'staffing and security costs.'},
            {'role': 'Student', 'text': 'Thank you.'},
            {'role': 'AI',
             'text': 'A trial period with usage counts would show whether extended hours are used enough to '
                     'justify the cost.'},
            {'role': 'Student', 'text': 'THIS LOOKS CORRECT!!'},
            {'role': 'AI',
             'text': 'Surveys of non-users can also reveal whether opening hours are the main barrier.'},
            {'role': 'Student', 'text': 'Good answer'}],
  'submitted_at': '2026-09-25T02:20:00+00:00'},
 {'ref': 'SYN-110',
  'student': 'hcoo867',
  'topic': 'Very short answer',
  'final_text': 'Access improves wellbeing.',
  'turns': [{'role': 'Student', 'text': 'Summarise the value of public transport in three words.'},
            {'role': 'AI', 'text': 'Access improves wellbeing.'},
            {'role': 'Student', 'text': 'Why those words rather than cost or speed?'}],
  'submitted_at': '2026-09-25T09:10:00+00:00'},
 {'ref': 'SYN-111',
  'student': 'acoa536',
  'topic': 'Rooftop solar for households',
  'final_text': 'Households that consume most of their electricity in daylight hours can cut their power '
                'bills with rooftop panels, but how much they save varies with system size, sunshine levels '
                'and export payments.',
  'turns': [{'role': 'Student', 'text': 'Do rooftop solar panels reduce household power bills?'},
            {'role': 'AI',
             'text': 'Rooftop solar lowers the electricity bills of households that use much of their power '
                     'during the day, although the savings depend on panel size, local sunshine and the '
                     'price paid for exported electricity.'},
            {'role': 'Student', 'text': 'Great, that makes sense.'}],
  'submitted_at': '2026-09-26T03:33:00+00:00'},
 {'ref': 'SYN-112',
  'student': 'rnav609',
  'topic': 'Household waste',
  'final_text': 'Kerbside recycling works best when households can sort materials easily, collection days '
                'are predictable and contamination is reported back to residents so that mistakes are '
                'corrected quickly.\n'
                '\n'
                'Composting food scraps keeps organic material out of landfill, where it would release '
                'methane, and produces a soil improver that gardeners and farms can use.\n'
                '\n'
                'A council should publish contamination rates each quarter so residents can see whether '
                'sorting is improving.',
  'turns': [{'role': 'Student', 'text': 'Describe how kerbside recycling can be made to work.'},
            {'role': 'AI',
             'text': 'Kerbside recycling works best when households can sort materials easily, collection '
                     'days are predictable and contamination is reported back to residents so that mistakes '
                     'are corrected quickly.'},
            {'role': 'Student', 'text': 'How does composting reduce landfill waste?'},
            {'role': 'AI',
             'text': 'Composting food scraps keeps organic material out of landfill, where it would release '
                     'methane, and produces a soil improver that gardeners and farms can use.'},
            {'role': 'Student', 'text': 'Interesting.'}],
  'submitted_at': '2026-09-26T07:08:00+00:00'}]
