import sqlite3
import json

# DB Name
DB_NAME = "test_suite.db"

def setup_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"Resetting {DB_NAME} with FINAL USER-PROVIDED test cases...")

    # 1. CLEANUP
    cursor.executescript("""
        DROP TABLE IF EXISTS test_run_results;
        DROP TABLE IF EXISTS test_runs;
        DROP TABLE IF EXISTS master_test_cases;
    """)

    # 2. CREATE TABLES
    cursor.execute("""
        CREATE TABLE master_test_cases (
            test_id TEXT PRIMARY KEY,
            description TEXT,
            user_input TEXT,
            expected_output_json TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE test_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_score INTEGER,
            status_summary TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE test_run_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            test_id TEXT,
            user_input TEXT,
            expected_output_json TEXT,
            actual_output_json TEXT,
            score INTEGER,
            status TEXT,
            mistakes TEXT,
            FOREIGN KEY(run_id) REFERENCES test_runs(run_id),
            FOREIGN KEY(test_id) REFERENCES master_test_cases(test_id)
        )
    """)

    # 3. POPULATE TEST CASES
    # Note: I have included the Top 3-5 critical results from your snippets to keep the verification sharp.
    
    test_cases = [
        # --- UNIVERSAL / INDEX SEARCH ---
        (
            "TC_001", 
            "Universal Search (Nifty)", 
            "nifty",
            # Expecting Spot -> Futures -> Other Indices
            json.dumps(["NIFTY", "NIFTY 27 JAN FUT", "NIFTY 24 FEB FUT", "NIFTY 30 MAR FUT", "NIFTY ALPHA 50"])
        ),
        (
            "TC_002", 
            "Typo Correction (Nifti)", 
            "nifti",
            # Fuzzy match 'nifti' -> 'NIFTY' -> Spot + Futures
            json.dumps(["NIFTY", "NIFTY 27 JAN FUT", "NIFTY 24 FEB FUT", "NIFTY 30 MAR FUT"])
        ),
        
        # --- DERIVATIVES: EXPLICIT TYPES ---
        (
            "TC_003", 
            "Explicit Futures (Fut)", 
            "nifty fut",
            # Explicit 'fut' tag -> Spot + Futures only
            json.dumps(["NIFTY", "NIFTY 27 JAN FUT", "NIFTY 24 FEB FUT", "NIFTY 30 MAR FUT"])
        ),
        (
            "TC_004", 
            "Explicit Month (Jan)", 
            "nifty jan",
            # 'jan' -> Nifty Spot + Jan Futures
            json.dumps(["NIFTY", "NIFTY 27 JAN FUT"])
        ),
        (
            "TC_005", 
            "Explicit Month (Mar)", 
            "nifty mar",
            # 'mar' -> Nifty Spot + Mar Futures
            json.dumps(["NIFTY", "NIFTY 30 MAR FUT"])
        ),
        (
            "TC_006", 
            "Month with No Derivs (Apr)", 
            "nifty apr",
            # 'apr' -> No futures exist, show only Spot
            json.dumps(["NIFTY"])
        ),
        
        # --- DERIVATIVES: OPTIONS (GENERIC) ---
        (
            "TC_007", 
            "Generic Call Options (CE)", 
            "nifty ce",
            # 'ce' -> Spot + Nearest CE options sorted by Strike Ascending
            json.dumps(["NIFTY", "NIFTY 20 JAN 23950 CE", "NIFTY 20 JAN 24000 CE", "NIFTY 20 JAN 24050 CE"])
        ),
        (
            "TC_008", 
            "Generic Put Options (PE)", 
            "nifty pe",
            # 'pe' -> Spot + Nearest PE options sorted by Strike Ascending
            json.dumps(["NIFTY", "NIFTY 20 JAN 23950 PE", "NIFTY 20 JAN 24000 PE", "NIFTY 20 JAN 24050 PE"])
        ),
        
        # --- DERIVATIVES: SPECIFIC DATES ---
        (
            "TC_009", 
            "Search by Day (20)", 
            "nifty 20",
            # '20' matches '20 JAN'. Shows Options expiring 20 Jan.
            json.dumps(["NIFTY", "NIFTY 20 JAN 23950 PE", "NIFTY 20 JAN 23950 CE", "NIFTY 20 JAN 24000 CE"])
        ),
        (
            "TC_010", 
            "Search by Date (3 Feb)", 
            "nifty 3 feb",
            # Explicit Date -> Spot + Options for that specific expiry
            json.dumps(["NIFTY", "NIFTY 3 FEB 23950 CE", "NIFTY 3 FEB 23950 PE", "NIFTY 3 FEB 24000 CE"])
        ),
        
        # --- GLOBAL SEARCH (NO SYMBOL) ---
        (
            "TC_011", 
            "Global Date Search (20 Jan)", 
            "20 jan",
            # Global search for '20 jan'. Shows Nifty Weekly Options.
            json.dumps(["NIFTY 20 JAN 23950 PE", "NIFTY 20 JAN 23950 CE", "NIFTY 20 JAN 24000 CE"])
        ),
        (
            "TC_012", 
            "Global Date Search (Sensex)", 
            "22 jan",
            # Global search '22 jan' matches Sensex expiry.
            json.dumps(["SENSEX 22 JAN 76100 CE", "SENSEX 22 JAN 76100 PE", "SENSEX 22 JAN 76200 CE"])
        ),
        (
            "TC_013", 
            "Global Strike Search", 
            "27000",
            # Search '27000' -> Finds Nifty Options across various expiries (20 Jan, 27 Jan, etc)
            json.dumps(["NIFTY 20 JAN 27000 PE", "NIFTY 20 JAN 27000 CE", "NIFTY 27 JAN 27000 PE"])
        ),
        
        # --- STRIKE SEARCH (WITH SYMBOL) ---
        (
            "TC_014", 
            "Specific Strike (26000)", 
            "nifty 26000",
            # Nifty + 26000 -> Spot + 26000 options (Sorted by Expiry: 20 Jan < 27 Jan)
            json.dumps(["NIFTY", "NIFTY 20 JAN 26000 PE", "NIFTY 20 JAN 26000 CE", "NIFTY 27 JAN 26000 PE", "NIFTY 27 JAN 26000 CE"])
        ),
        (
            "TC_015", 
            "Shorthand Strike (26k)", 
            "nifty 26k",
            # '26k' -> Parses to 26000. Same result as above.
            json.dumps(["NIFTY", "NIFTY 20 JAN 26000 PE", "NIFTY 20 JAN 26000 CE", "NIFTY 27 JAN 26000 PE"])
        ),
        (
            "TC_016", 
            "Decimal Strike (26.5k)", 
            "nifty 26.5k",
            # '26.5k' -> Parses to 26500.
            json.dumps(["NIFTY", "NIFTY 20 JAN 26500 CE", "NIFTY 20 JAN 26500 PE", "NIFTY 27 JAN 26500 CE"])
        ),
        
        # --- EQUITY / STOCK SEARCH ---
        (
            "TC_017", 
            "Equity Search (Reliance)", 
            "reliance",
            # Exact Match -> Spot + Futures + Spot(Duplicate/NSE/BSE)
            json.dumps(["RELIANCE", "RELIANCE 27 JAN FUT", "RELIANCE 24 FEB FUT", "RELIANCE 30 MAR FUT", "RELIANCE"])
        ),
        (
            "TC_018", 
            "Equity + Strike (Distance)", 
            "reliance 1401",
            # '1401' -> Matches closest strikes (1400, 1410)
            json.dumps(["RELIANCE", "RELIANCE 27 JAN 1400 PE", "RELIANCE 27 JAN 1400 CE", "RELIANCE 27 JAN 1410 CE"])
        ),
        (
            "TC_019", 
            "Prefix Search (Rel)", 
            "rel",
            # 'rel' -> Matches RELTD, RELAXO, RELIANCE etc.
            json.dumps(["RELTD", "RELAXO", "RELAXO", "RELCHEMQ"])
        ),
        (
            "TC_020", 
            "Generic Prefix (Bank)", 
            "bank",
            # 'bank' -> Matches BANKA, BANKBARODA, BANKNIFTY
            json.dumps(["BANKA", "BANKBARODA", "BANKBARODA", "BANKEX"])
        ),
        (
            "TC_021", 
            "Equity No Derivs (MRF)", 
            "mrf",
            # MRF has no futures in DB -> Returns Spot + Duplicate Spot
            json.dumps(["MRF", "MRF"])
        )
    ]

    cursor.executemany("INSERT INTO master_test_cases VALUES (?, ?, ?, ?)", test_cases)
    conn.commit()
    conn.close()
    print(f"Database populated with {len(test_cases)} user-provided test cases.")

if __name__ == "__main__":
    setup_db()