import sys
import os
# Add parent directory to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.search_service import search_logic

def run_interactive_tool():
    db = SessionLocal()
    
    print("\n" + "="*50)
    print("   MARKET SEARCH TOOL")
    print("   Type 'exit' to quit.")
    print("="*50 + "\n")

    while True:
        try:
            query = input("Search > ").strip()
        except KeyboardInterrupt:
            break
            
        if query.lower() in ['exit', 'quit']:
            break
        if not query:
            continue

        result = search_logic(query, db)

        if result.get("status") == "no_match":
            print(f"❌ {result['message']}\n")
            continue

        print(f"\n✅ Intent Parsed: {result.get('result_type', 'DERIVATIVES')}")
        print(f"   Underlying: {result.get('underlying')}")
        
        matches = result.get("matches", [])
        
        if not matches:
            if "data" in result:
                d = result["data"]
                print(f"\n   🎯 Found: {d['symbol']} ({d['type']})")
            else:
                print("   ⚠️ No specific instruments found.")
        else:
            print(f"\n   {'SYMBOL':<25} {'TYPE':<10} {'DISPLAY NAME'}")
            print("   " + "-"*60)
            for m in matches:
                print(f"   {m['symbol']:<25} {m['type']:<10} {m['display_name']}")
        print("\n")

if __name__ == "__main__":
    run_interactive_tool()