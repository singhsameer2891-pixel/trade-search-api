# 🚀 Smart Trade Search Engine (Intent Parser)

**Live Demo:** [https://trade-search-api.onrender.com/docs](https://trade-search-api.onrender.com/docs)  
*(Try inputs: "Nifty 27 Jan", "Reliance 26k", "Nifti", "20 Jan")*

---

## 💡 The Product Context

**The Friction:** Traditional trading app search bars are rigid. Users are forced to navigate complex filters (Symbol → Instrument Type → Expiry → Strike) just to find a single contract.

**The Solution:** A "Google-like" financial search engine that parses natural language. It accepts messy, human inputs like *"Nifti 26k"* and instantly infers the user's intent to return the exact Options Chain or Futures contract in **<50ms**.

**The Role:** Built by a Product Manager who codes—solving for UX latency and data ambiguity simultaneously.

---

## 🧠 Engineering Wins: 3 Key Problems Solved

This isn't just a database lookup. It is an **Intent Parsing Engine** that handles ambiguity through three distinct layers of logic.

### 1. Contextual Intent Parsing (Dates & Sorting)
**🛑 The Problem:**
Users often search by date (e.g., *"20 Jan"*) without specifying a symbol. A standard SQL query would fail or return random matches.

**✅ My Solution:**
I built a tokenizer that detects date entities. If a date is found without a symbol, the system switches to **"Global Expiry Mode"**.
* **Input:** `"20 Jan"`
* **Logic:**
    1.  Parse "20 Jan" to `2025-01-20`.
    2.  Query *all* active option contracts expiring on this date.
    3.  **Smart Sort:** Results are not random; they are ranked by liquidity (Nifty > BankNifty > Stocks) and organized by Call/Put pairs.

### 2. Fuzzy Matching & Shorthand Expansion
**🛑 The Problem:**
Mobile users have "fat fingers" and use trader shorthand.
* Typo: *"Nifti"* instead of "NIFTY".
* Shorthand: *"26k"* instead of "26000".

**✅ My Solution:**
I integrated a layered search strategy using **Levenshtein Distance** (`TheFuzz`) and Regex.
* **Typo Correction:** *"Nifti"* scores >80% match against *"NIFTY"*, triggering an auto-correction.
* **Regex Expansion:** The parser identifies `\d+k` patterns. *"26k"* is mathematically expanded to `26000` before hitting the database.
* **Result:** The query *"nifti 26k"* automatically returns **Nifty 26000 CE/PE** for the nearest expiry.

### 3. "Nearest Strike" Proximity Logic
**🛑 The Problem:**
Users rarely remember the exact strike prices available in the market.
* **Input:** *"Reliance 1401"*
* **Reality:** Reliance strikes exist at 1400 and 1420. There is no "1401" contract.
* **Standard Behavior:** Returns "No Results."

**✅ My Solution:**
The API understands numeric proximity. It treats "1401" not as a text string, but as a **numerical target**.
* The system searches for contracts where `abs(StrikePrice - UserInput)` is minimized.
* **Outcome:** It gracefully returns **Reliance 1400 CE/PE**, keeping the user in the flow.

---

## 🛠 Tech Stack & Architecture

* **Core:** Python 3.9, FastAPI (Async)
* **Search Logic:** Regex Tokenization + Fuzzy Matching
* **Database:** SQLite (SQLAlchemy ORM)
* **DevOps:** Render (Cloud Hosting), GitHub Actions (CI/CD)
* **Quality:** Custom Regression Testing Framework

---

## ⚙️ Setup & Deployment

<details>
<summary><strong>👉 Click to expand Local Setup Commands</strong></summary>

### 1. Installation
```bash
# Clone & Setup
git clone [https://github.com/YOUR_USERNAME/smart-trade-search-engine.git](https://github.com/YOUR_USERNAME/smart-trade-search-engine.git)
cd smart-trade-search-engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Locally
```bash
uvicorn app.main:app --reload
# Access API at http://localhost:8000/docs
```

### 3. Run Test Suite
```bash
python tests/test_runner.py
```
</details>

<details>
<summary><strong>👉 Click to expand Cloud Deployment (Render)</strong></summary>

This project is configured for Infrastructure-as-Code.

1. Push code to GitHub.
2. Render automatically detects `render.yaml`.
3. **Build trigger:** `pip install -r requirements.txt`.
4. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
</details>

---

## 🧪 Quality Control

To prevent regression issues (fixing one bug but breaking another), I built a custom Regression Testing Framework (`test_runner.py`).

* **Golden Dataset:** A suite of 20+ complex test cases covering edge cases like "Nifty 26.5k", "Rel 1400", and "BankNifty Jan".
* **Workflow:** I run this suite locally before every commit to ensure 100% logic integrity.

---

## 🔗 API Usage

* **Base URL:** `https://trade-search-api.onrender.com`

**cURL Example:**
```bash
curl -X 'GET' \
  '[https://trade-search-api.onrender.com/search?q=nifty%2027%20jan](https://trade-search-api.onrender.com/search?q=nifty%2027%20jan)' \
  -H 'accept: application/json'
```