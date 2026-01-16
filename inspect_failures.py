import sqlite3
import json

conn = sqlite3.connect('test_suite.db')
cursor = conn.cursor()

# Get the latest run ID
cursor.execute("SELECT MAX(run_id) FROM test_runs")
latest_run_id = cursor.fetchone()[0]

print(f"--- Inspecting Failures for Run #{latest_run_id} ---\n")

cursor.execute("""
    SELECT test_id, user_input, expected_output_json, actual_output_json 
    FROM test_run_results 
    WHERE run_id = ? AND status = 'FAIL'
""", (latest_run_id,))

rows = cursor.fetchall()

for test_id, user_input, exp_json, act_json in rows:
    expected = json.loads(exp_json)
    actual = json.loads(act_json)
    
    print(f"FAILED: {test_id} (Input: '{user_input}')")
    print(f"{'EXPECTED':<30} | {'ACTUAL (What DB returned)':<30}")
    print("-" * 65)
    
    # Print side-by-side
    max_len = max(len(expected), len(actual))
    for i in range(max_len):
        e_item = expected[i] if i < len(expected) else ""
        a_item = actual[i] if i < len(actual) else ""
        
        # Mark mismatch with a *
        marker = " " if e_item == a_item else "*"
        print(f"{e_item:<30} | {a_item:<30} {marker}")
    
    print("\n" + "="*65 + "\n")

conn.close()