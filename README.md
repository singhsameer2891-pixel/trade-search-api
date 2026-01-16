# 🚀 Trade Search API: The Master Guide

## 1. Project Overview
We built a smart, typo-tolerant **Financial Instrument Search Engine** (API) using Python (FastAPI).

* **Goal:** Allow users to search for stocks (e.g., "Reliance"), indices ("Nifty"), or specific derivatives ("Nifty 27 Jan 26000 CE").
* **Key Feature:** "Intent Parsing" — The system understands if you want the Stock (Spot), Futures (Derivatives), or Options based on natural language input.

---

## 2. Core Concepts & "Aha!" Moments

### A. The "Twin Identity" Problem (BSE vs. NSE)
* **Issue:** The database contained duplicates (e.g., `DIXON` exists twice). Searching for "DIXON" often returned the BSE version (which has no derivatives), causing the search to show zero futures.
* **Solution (The Paternity Test):** We stopped guessing based on flags like "Segment ID." Instead, we query the DB: *"Which of these two DIXONs actually has children (futures) linked to it?"* That one is treated as the True Underlying.

### B. The "Time Translator" (Sorting Futures)
* **Issue:** Database dates are strings (`"27-JAN-25"`). Python sorts strings alphabetically, meaning "APR" comes before "JAN".
* **Solution:** We built a `parse_date` helper that converts strings to time objects.
* **Garbage Collection:** Invalid dates are assigned to `Year 9999` so they drop to the bottom of the list.

### C. Fuzzy Logic (Typo Tolerance)
* **Technique:** We used `TheFuzz` library (Levenshtein distance).
* **Logic:**
    1.  Try **Exact Match** (Fastest).
    2.  Try **Prefix Match** ("REL" → "RELIANCE").
    3.  Try **Fuzzy Match** ("NIFTI" → "NIFTY").
* **Constraint:** We set a score threshold (80/100) to prevent wild guesses.

### D. The "Amnesia" Constraint (Cloud Deployment)
* **Learning:** Free cloud servers (like Render/Heroku) differ from your laptop. They use **Ephemeral Filesystems**.
* **Impact:** You can **read** from your SQLite database perfectly. But if your API writes new data to it, that data is **wiped** every time the server restarts.
* **Fix:** Treat the DB as "Read-Only" in production. To add data, add it locally, commit to Git, and push.

---

## 3. Local Setup & Development Commands

### Setting Up the Environment
Always work inside a Virtual Environment (`venv`) to keep dependencies isolated.

```bash
# 1. Create the venv (One time only)
python3 -m venv venv

# 2. Activate the venv (Every time you open terminal)
# Mac/Linux:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# 3. Install Dependencies
pip install fastapi uvicorn sqlalchemy thefuzz python-levenshtein
```

### Running the Code

```bash
# Run the API locally (Auto-reloads on save)
uvicorn main:app --reload

# Run the Test Runner
python test_runner.py

# Run the DB Setup (Resets Test Data)
python setup_test_db.py
```

---

## 4. The Testing Framework (Regression Testing)

We built a custom automated testing suite to prevent "Fixing one thing breaking another."

### Architecture (3 Tables)
1.  **`master_test_cases`:** The "Golden Source" (Input vs. Expected Output).
2.  **`test_runs`:** History of every test execution.
3.  **`test_run_results`:** Detailed logs of what passed/failed in each run.

### Scoring Logic
* **Perfect Match:** 100 Points.
* **Missing/Extra Item:** -10 Points per item.
* **Wrong Sequence:** -5 Points per item.
* **Status:** Only 100 is a PASS.

### Debugging Commands
If a test fails, we use scripts to inspect *why* (comparing Expected vs Actual side-by-side).

```bash
# Inspect specific failure details
python inspect_failures.py
```

---

## 5. Version Control (Git Workflow)

### The "Save & Sync" Loop
Use this every time you finish a task.

```bash
# 1. Stage all changes (Prepare to save)
git add .

# 2. Commit (Save locally with a note)
git commit -m "Fixed the MRF issue and updated tests"

# 3. Push (Send to GitHub & Trigger Render Deploy)
git push
```

### Handling the Database
Git ignores certain files by default. If your `.db` file isn't uploading:

```bash
# Force add the database file
git add -f test_suite.db
git commit -m "Update database"
git push
```

---

## 6. Deployment (Render.com)

### Configuration Files
To deploy successfully, your project **must** have these two files in the root folder:

#### A. `requirements.txt` (The Clean Version)
* **Issue:** `pip freeze` on Mac captures local file paths (`/AppleInternal/...`) which crash Linux servers.
* **Correct Content:**
    ```text
    fastapi==0.109.0
    uvicorn==0.27.0
    sqlalchemy==2.0.25
    thefuzz==0.22.1
    python-levenshtein==0.23.0
    ```

#### B. `render.yaml` (The Blueprint)
Tells Render how to build the app so you don't have to configure settings manually.

```yaml
services:
  - type: web
    name: trade-search-api
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.0
```

### Troubleshooting Deployment
* **Error:** `Command not found: uvicorn`
    * **Fix:** Add `uvicorn` to `requirements.txt`.
* **Error:** `Port detection timeout` or `Health Check Failed`
    * **Fix:** Ensure your start command uses `--host 0.0.0.0` (Public) and `--port $PORT` (Dynamic), **NOT** `127.0.0.1` or port `8000`.

---

## 7. Cheat Sheet: API Access

Once deployed, anyone can access your API using these methods.

**Base URL:** `https://trade-search-api.onrender.com`

### cURL Command (Terminal)
```bash
curl -X 'GET' \
  'https://trade-search-api.onrender.com/search?q=nifty' \
  -H 'accept: application/json'
```

### Browser Test
Visit `https://trade-search-api.onrender.com/docs` for the interactive Swagger UI.

---

## 8. Database Debugging (SQL)

When in doubt about the data, use these SQL queries (via Python or DB Browser).

**Find "Orphan" Instruments (No Derivatives):**
```sql
SELECT * FROM Instrument 
WHERE Symbol = 'MRF' 
AND InstrumentType = 1;
```

**Find Children (Derivatives):**
```sql
SELECT * FROM Instrument 
WHERE UnderlyingInstrumentId = [ID_FROM_ABOVE];
```

---

## Summary of Success
* ✅ **Built:** A robust, fuzzy-search API for financial data.
* ✅ **Solved:** Complex data mapping issues (Twin Identities).
* ✅ **Automated:** Quality control via a strict regression testing suite.
* ✅ **Deployed:** Live on the cloud via CI/CD pipeline (Git -> Render).