# Lane 2 Evidence Review

INFOMGMT 399 · Team HAHA

A small web application that helps markers review how students used AI in Lane 2 assessments.

* **Students** sign in and submit their final work together with their AI interaction history.
* **The server** checks the submission and stores everything in a database. An **OpenAI model** rates how the student responded to each AI answer (this does all of the critique flagging), and a **wording comparison** flags paragraphs of the final text that closely match an AI answer.
* **Markers** sign in, see every submission in a review queue, inspect the flagged evidence, record their own decisions and notes, and complete the review.

Flags are reasons to look closer, not conclusions. No grade is produced.
All data in this project is fictional. Do not enter real student information.

---

## How to open the website

The website runs on your own computer. You start it from a terminal window, then open it in your web browser. You only need to do **Steps 1 to 4 once**. Every other time, you only need **Steps 2 and 5**.

### What you need

**Python 3.9 or newer.** To check whether you already have it, open a terminal (see Step 2) and type:

* Windows: `py --version`
* Mac / Linux: `python3 --version`

If you see something like `Python 3.12.4`, you are ready. If you see an error such as *"py is not recognized"* or *"Python was not found"*, install Python first:

1. Go to **https://www.python.org/downloads/** and download the latest version for your computer.
2. Run the installer. On Windows, tick **"Add python.exe to PATH"** on the first screen, then choose **Install Now**.
3. Close any open terminal windows and open a new one before continuing.

You also need an internet connection for Step 4 (the one-off install).

### Windows

**Step 1. Unzip the folder.**
Right-click the downloaded `lane2-app.zip` and choose **Extract All**, then **Extract**. Do not run the app from inside the zip file. Open the extracted folder and keep going into it until you can see the file `app.py` (sometimes the folder is inside another folder with the same name). That folder is your **project folder**.

**Step 2. Open Command Prompt in the project folder.**
The easiest way:

1. Open the project folder in File Explorer (the one containing `app.py`).
2. Click once in the address bar at the top of the window.
3. Type `cmd` and press **Enter**.

A black Command Prompt window opens, already in the right place. You should see a line ending in `lane2-app>`. To double-check, type `dir` and press Enter: the list should include `app.py`.

*Another way:* press **Windows + R**, type `cmd`, press Enter, then type `cd` followed by a space and the folder path in quotes, for example:
`cd "C:\Users\YourName\Downloads\lane2-app\lane2-app"`

**Step 3. Check Python.**
Type this and press Enter:
```
py --version
```
You should see a version number such as `Python 3.14.8`.

**Step 4. Install the one required package (first time only).**
```
py -m pip install -r requirements.txt
```
Wait until it finishes and you are back at the `>` prompt. Messages ending in "Successfully installed" (or "Requirement already satisfied") are fine.

**Step 5. Start the website.**
```
py app.py
```
After a moment you should see:
```
Lane 2 Evidence Review is running. Open http://127.0.0.1:5000 in your browser.
Leave this window open while you use it. Press Ctrl+C to stop.
```
**Leave this window open.** The website only works while this window is running.

**Step 6. Open it in your browser.**
Open Chrome, Edge or Firefox and go to **http://127.0.0.1:5000**

**Step 7. Sign in.**
Choose **Student sign in** or **Marker sign in** and use one of the test accounts below.

**To stop the website:** click the Command Prompt window and press **Ctrl+C** (or just close the window).

### Mac / Linux

Open **Terminal**, then:

```
cd /path/to/lane2-app          # the folder that contains app.py
python3 --version
python3 -m pip install -r requirements.txt     # first time only
python3 app.py
```

Then open **http://127.0.0.1:5000** in your browser. If the install step says the environment is "externally managed", create a private environment first and then repeat the install and start commands:

```
python3 -m venv venv
source venv/bin/activate
```

---

## Turn on the OpenAI critique check

The critique flags come from an OpenAI model, not from fixed rules. It reads every student reply that follows an AI answer and rates it as **substantive**, **generic** or **blind acceptance**. Generic replies and blind acceptance become flags in the marker's queue, labelled "LLM-assisted"; replies rated substantive are shown as context. **Without a key and without saved results, the website still runs, but it creates no critique flags** (only the wording-comparison flags), and the review page says why. Every quote the model gives is checked against the student's real text, a flag whose quote cannot be found is thrown away, and the marker still makes every decision.

Student text is sent to OpenAI when a key is set, so use **fictional data only**. Each submission is one small request, so the whole project should cost cents (check OpenAI's pricing page for the current price of the model you use).

**Teachers and anyone else running this project do not need a key, as long as `llm_cache.json` is included.** Results from your own run are saved in that file and are shown to everyone. **Run step 4 below before you submit, and keep `llm_cache.json` in the folder you hand in**, otherwise the fictional submissions will show no critique flags for anyone without a key.

### Set it up (Windows Command Prompt, about 10 minutes)

1. **Get a key.** Go to **https://platform.openai.com**, sign in, add a few dollars of credit under billing, then open **API keys** and create a new secret key. Copy it straight away because it is only shown once. Never paste the key into a file, a chat, your report or the zip.
2. **Open Command Prompt in the project folder** (see "Windows" Step 2 above) and give it the key. This lasts only for this window:
   ```
   set OPENAI_API_KEY=paste-your-key-here
   ```
   (No quotation marks. On Mac / Linux use `export OPENAI_API_KEY=paste-your-key-here`.)
3. **Test it:**
   ```
   py check_openai.py
   ```
   You want to see *"The connection works."* If not, the message says what to fix (see the table below).
4. **Rate the existing submissions** (this also saves the results for teachers):
   ```
   py run_critique_checks.py
   ```
5. **Start the website in the same window:**
   ```
   py app.py
   ```
   New student submissions are now checked as they arrive. In the marker page, open a submission and look for flags marked "LLM-assisted", and see the status under **Analysis method**.
6. **For the report (optional):** compare a simple fixed-phrase baseline with the model on 36 labelled replies:
   ```
   py eval/evaluate_flags.py
   ```
   This writes `eval/results.md`. The labels in `eval/labelled_replies.py` are a draft, so read them and correct any you disagree with before using the numbers.

### Settings you can change

| Setting (set it the same way as the key) | What it does |
|---|---|
| `LANE2_OPENAI_MODEL` | The model name. Default `gpt-5.4-mini`. Model names change, so copy an exact name from OpenAI's models page if the default is rejected. |
| `LANE2_LLM_MODE` | `auto` (default: live if a key is set, otherwise saved results only), `off`, or `mock` (a simple stand-in used for practice runs, clearly labelled "Simulated check"). |
| `LANE2_LLM_HOURLY_LIMIT` | Most live OpenAI requests per hour. Default 30. This stops a mistake from costing money. |

### If the check does not work

| What `check_openai.py` says | What to do |
|---|---|
| No key found | You set the key in a different window, or it contains a typo. Set it again in this window. |
| OpenAI rejected the API key | The key was copied wrongly or deleted. Create a new one. |
| Could not use the model | Set `LANE2_OPENAI_MODEL` to a model name listed on OpenAI's models page. |
| Rate limit or no credit | Add credit to the OpenAI account, or wait a minute and try again. |
| Could not reach OpenAI | Check the internet connection. |

If the check fails while the app is running, the submission is still saved (with its wording-comparison flags), and the marker page shows why the check did not run, with a button to try again.

---

## Test accounts

These accounts are for local testing only.

| Role    | Username  | Password         |
|---------|-----------|------------------|
| Marker  | marker1   | marker-pass-1    |
| Student | aiye355   | student-pass-1   |
| Student | hluo185   | student-pass-2   |
| Student | acoa536   | student-pass-3   |
| Student | hcoo867   | student-pass-4   |

Each account only works on its own sign-in page: student accounts on **Student sign in**, the marker account on **Marker sign in**.

The queue also contains fictional submissions from two other students, `rnav609` and `kugn020`. They appear in the marker's queue, but they do not have a login.

## Try the main journey

1. Sign in as `aiye355` on **Student sign in** and submit some fictional work with an AI history, one turn per line. The turns must alternate between `Student:` and `AI:`:
   ```
   Student: Explain solar panels.
   AI: Solar panels turn sunlight into electricity for homes.
   Student: Thanks.
   ```
   Tip: use the same sentence as your final submission to see an overlap flag, and a reply such as `Student: Thanks` to see a critique flag (this needs the critique check turned on, see above).
2. Sign out, then sign in as `marker1` on **Marker sign in**.
3. Your submission is at the bottom of the review queue under `aiye355`. Open it, inspect the flags, choose **Accept flag**, **Dismiss flag** or **Need more context** with a reason for each flag, save an overall note, and complete the review. **Export review** opens a readable PDF report (flags, decisions, notes, transcript and final submission) that you can save or print.
4. Stop and restart the website (Step 5). Your submission, decisions and notes are still there because they are stored in the database.

## Resetting the data

Stop the website, delete the file `instance/lane2.db`, and start it again. A fresh database with the fictional data is created.

If you open a newer version of the project with an older database, the website looks after it automatically and never deletes anything. A database from the two previous versions (2.2 or 2.3) is upgraded in place, keeping your submissions, notes and decisions, and a copy is saved as `instance/lane2.backup-<date and time>.db`. The old phrase-list flags no longer exist, so decisions saved on them cannot be kept; the critique check's flags (from its saved results) take their place and need a new decision. A much older database is moved to a backup file of the same kind and a fresh one is created.

## If something goes wrong

| What you see | What to do |
|---|---|
| `'py' is not recognized` or `Python was not found` | Python is not installed or not on your PATH. Follow "What you need" above, then open a **new** terminal. On Windows, if the message mentions the Microsoft Store, you can also turn off the Python entries in **Settings > Apps > Advanced app settings > App execution aliases**. |
| `No module named flask` | The install step was skipped. Run `py -m pip install -r requirements.txt` again from the project folder. |
| `can't open file ... app.py` | The terminal is not in the project folder. Repeat Step 2 and check that `dir` lists `app.py`. |
| `Address already in use`, or the website opens something unexpected | Another copy is still running, or another program uses port 5000. Close other Command Prompt windows running the app, or use another port: on Windows type `set LANE2_PORT=5001` then `py app.py`, and open http://127.0.0.1:5001 instead. |
| The page says "This site can't be reached" | The website is not running. Check the Command Prompt window is still open and shows the "is running" message. |
| The page looks out of date after an update | Refresh with **Ctrl+F5**. |
| "Turns must alternate between Student: and AI:" when submitting | The AI history needs a `Student:` turn, then an `AI:` turn, then `Student:` again, and so on. If you copied a chat where you sent two messages in a row, join them into one `Student:` turn. |

## Run the automated checks (optional)

```
py -m unittest discover -s tests -v
```
(Mac / Linux: `python3 -m unittest discover -s tests -v`.) These use a temporary database and do not touch `instance/lane2.db`.

## What is in the folder

| File / folder        | Purpose |
|----------------------|---------|
| `app.py`             | The web server: sign-in, student and marker routes, database access |
| `analysis.py`        | The wording comparison (text overlap) and the wording-overlap measure |
| `pdf_report.py`      | Builds the readable PDF review report (needs no extra packages) |
| `llm_flags.py`       | The optional OpenAI critique check, with its safety checks |
| `check_openai.py`    | Tests your OpenAI key and model |
| `run_critique_checks.py` | Rates every submission and saves the results |
| `eval/`              | Labelled replies and a script that compares a simple phrase-list baseline (not used by the app) with the model |
| `llm_cache.json`     | Saved results of real OpenAI checks (created when you run them; contains no key) |
| `schema.sql`         | The database tables |
| `seed_data.py`       | Fictional test accounts and 12 fictional submissions |
| `templates/`         | The HTML pages (landing, sign-in, student, marker) |
| `static/`            | The stylesheet and page scripts |
| `tests/`             | Automated checks |
| `archive/`           | The earlier single-page prototype, kept for comparison |

## Known limitations

* Intended for local use and for the teaching team to test. It uses Flask's built-in server, which is not suitable for production.
* Stored data is not encrypted, there is no password reset, no login attempt limit, and no data retention policy.
* The wording comparison is deliberately narrow, and neither it nor the critique check has been validated on real student work.
* Critique flags depend on the OpenAI model. Without a key or saved results, only wording-comparison flags appear.
* The PDF report is plain by design: one column, standard fonts, and text outside the Western European character set (for example emoji) appears as `?`.
* The OpenAI critique check can be wrong. It sees only the text supplied, and a human must make every decision. The wording-overlap bar measures matching phrases, not who wrote the text, and does not detect paraphrase.
* No connection to a university system or learning management system, no AI model, and no automatic grade.

## Optional: putting it online

Most free hosting services can run it, but a free host's disk is usually reset on restart, so the database would be reset too. If you deploy, install `gunicorn` (`pip install gunicorn`), use the start command `gunicorn app:app`, and set an environment variable `LANE2_SECRET_KEY` to a long random value.
