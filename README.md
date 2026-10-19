# Lane 2 Evidence Review

**INFOMGMT 399 · Group 9 — Team HAHA**  
**Live application:** https://lane2review.com

Lane 2 Evidence Review is a web application that helps university markers examine how students engaged with generative AI during assessments. It brings together a student's final submission, AI interaction transcript and review cues so that markers can inspect evidence in context and record their own decisions.

**The application supports human judgement; it does not grade students or determine academic misconduct.** All demonstration data is fictional. Do not enter real student information.

## Access the application

Open **https://lane2review.com** in a browser. No installation is required for the hosted demonstration.

- **Student interface:** Submit written work and an AI interaction transcript.
- **Marker interface:** Browse submissions, inspect review cues and original context, record decisions and notes, and export a PDF review report.

Demonstration login credentials are supplied separately to authorised reviewers; no live passwords are published in this repository.

## Main features

- **AI-assisted critique:** An OpenAI model classifies student replies to AI responses as substantive, generic or blind acceptance. Generic replies and blind acceptance can become review cues.
- **Text-overlap analysis:** Phrase-based comparison highlights wording shared between the final submission and AI responses. Similarity does not prove authorship.
- **Evidence-led review:** Markers can read original transcript turns alongside flagged material, decide whether a cue warrants attention and save their notes.
- **PDF export:** Review information can be exported as a report.

If the OpenAI service is unavailable and no saved analysis is available, the application can still provide text-overlap results; live critique cues will not be generated.

## Technical overview

| Component | Technology |
| --- | --- |
| Interface | HTML, CSS and JavaScript |
| Application server | Python / Flask, served by Gunicorn |
| Data storage | SQLite |
| Critique analysis | OpenAI API |
| Hosting and persistent database volume | Railway |
| Source control and automatic deployments | GitHub |
| Domain and DNS | Cloudflare |

**Core flow:** Student submission and transcript → Flask validation and storage → AI critique and text-overlap checks → evidence presented to the marker → marker decisions and PDF export.

The hosted database is stored on a persistent Railway volume, separate from any local development database. Changes pushed to the repository's `main` branch trigger a Railway deployment.

## Run locally

Local setup is optional for users of the hosted website but is provided for source-code assessment and development.

1. Install Python 3.9 or newer.
2. Clone this repository or extract the submitted source-code ZIP.
3. Open a terminal in the folder containing `app.py` and run:

   ```bash
   python -m pip install -r requirements.txt
   python app.py
   ```

4. Visit **http://127.0.0.1:5000** (or the address printed in the terminal).

On Windows, `py` may be used in place of `python`. A fresh local database is populated with fictional seed data. **The seeded marker account does not have a usable default password**; contact the project team for a configured demonstration account or local setup assistance.

### Optional live OpenAI checks

Live critique analysis requires an OpenAI API key with API billing enabled. Set the `OPENAI_API_KEY` environment variable before launching the application; never place the key in source code or commit it to Git.

To check API connectivity, run:

```bash
python check_openai.py
```

For Railway, the application is served with:

```bash
gunicorn --bind 0.0.0.0:$PORT app:app
```

The Railway deployment uses `LANE2_DATABASE_PATH=/data/lane2.db` and securely configured environment variables, including `LANE2_SECRET_KEY` and `OPENAI_API_KEY`.

## Testing

Run the automated tests locally:

```bash
python -m unittest discover -s tests -v
```

The accompanying technical demonstration video explains the end-to-end workflow, processing logic, test scenarios, outcomes and known limitations.

## Limitations and responsible use

This is a **capstone prototype**, not a production-ready university assessment system.

- The dataset contains fictional student submissions and transcripts; no real-world educational validity is claimed.
- The application is not connected to a university learning management system.
- OpenAI classifications may be wrong or incomplete and depend on external API availability and credits.
- Text-overlap checks identify matching wording, not authorship or paraphrasing reliably.
- Additional security, privacy, backup, access-control and operational safeguards would be needed before handling real student data.
- All review cues require interpretation by a human marker. No automated grades or misconduct findings are produced.

**University of Auckland · INFOMGMT 399 · Group 9 — Team HAHA**  
*Academic demonstration project; not an official University of Auckland assessment platform.*
