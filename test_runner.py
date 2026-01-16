import sqlite3
import json
import logging
import sys
import os

sys.path.append(os.getcwd())

try:
    from search_service import search_logic
    from database import SessionLocal
except ImportError:
    print("ERROR: Could not import 'search_service' or 'database'.")
    sys.exit(1)

TEST_DB = 'test_suite.db'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestRunner")

def calculate_score_and_errors(expected, actual):
    score = 100
    errors = []

    exp_set = set(expected)
    act_set = set(actual)

    missing = exp_set - act_set
    extra = act_set - exp_set

    if missing:
        count = len(missing)
        score -= (count * 10)
        errors.append(f"Missing {count} items: {', '.join(missing)}")
    
    if extra:
        count = len(extra)
        score -= (count * 10)
        errors.append(f"Extra {count} items: {', '.join(extra)}")

    if score > 0:
        seq_errors = []
        for i in range(len(expected)):
            if i < len(actual) and expected[i] != actual[i]:
                score -= 5
                seq_errors.append(f"Pos {i}: Expected '{expected[i]}' != Got '{actual[i]}'")
        
        if seq_errors:
            errors.append("Sequence Errors: " + "; ".join(seq_errors))

    return max(0, score), " | ".join(errors) if errors else "None"

def run_tests():
    if not os.path.exists(TEST_DB):
        print(f"ERROR: {TEST_DB} not found. Run 'setup_test_db.py' first.")
        return

    test_conn = sqlite3.connect(TEST_DB)
    test_cursor = test_conn.cursor()
    market_db = SessionLocal()

    test_cursor.execute("INSERT INTO test_runs (total_score, status_summary) VALUES (0, 'IN_PROGRESS')")
    run_id = test_cursor.lastrowid
    logger.info(f"--- Starting Test Run #{run_id} ---")

    test_cursor.execute("SELECT test_id, user_input, expected_output_json FROM master_test_cases")
    cases = test_cursor.fetchall()

    run_total_score = 0
    total_cases = len(cases)

    print(f"\nRunning {total_cases} test cases...")
    print("-" * 80)
    print(f"{'ID':<8} {'INPUT':<15} {'SCORE':<8} {'STATUS':<8} {'MISTAKES'}")
    print("-" * 80)

    for test_id, user_input, expected_json in cases:
        expected_output = json.loads(expected_json)
        
        try:
            api_response = search_logic(user_input, market_db)
            if api_response.get('status') == 'success':
                full_actual = [x['display_name'] for x in api_response['matches']]
            else:
                full_actual = []
        except Exception as e:
            logger.error(f"Crash in {test_id}: {e}")
            full_actual = []

        # Slice actual to match expected length for comparison
        compare_len = len(expected_output)
        actual_sliced = full_actual[:compare_len]

        score, mistakes = calculate_score_and_errors(expected_output, actual_sliced)
        status = "PASS" if score == 100 else "FAIL"

        # [UPDATED] Insert new columns: user_input and expected_output_json
        test_cursor.execute("""
            INSERT INTO test_run_results 
            (run_id, test_id, user_input, expected_output_json, actual_output_json, score, status, mistakes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, 
            test_id, 
            user_input,                # NEW
            expected_json,             # NEW
            json.dumps(actual_sliced), 
            score, 
            status, 
            mistakes
        ))

        run_total_score += score
        
        # Shorten mistakes for console display
        mistakes_display = (mistakes[:40] + '...') if len(mistakes) > 40 else mistakes
        print(f"{test_id:<8} {user_input:<15} {score:<8} {status:<8} {mistakes_display}")

    avg_score = int(run_total_score / total_cases) if total_cases > 0 else 0
    test_cursor.execute("UPDATE test_runs SET total_score = ?, status_summary = ? WHERE run_id = ?", 
                        (avg_score, "COMPLETED", run_id))

    test_conn.commit()
    test_conn.close()
    market_db.close()

    print("-" * 80)
    print(f"Run Completed. Average Score: {avg_score}/100")

if __name__ == "__main__":
    run_tests()