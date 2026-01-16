from ..database import SessionLocal
from .search_service import search_logic

def run_interactive_tool():
    # 1. Connect to DB
    db = SessionLocal()
    
    print("\n" + "="*50)
    print("   MARKET SEARCH TOOL (Logic Flowchart Demo)")
    print("   Try: 'Reliance', 'Jan 26000', 'Nifty Jan Fut'")
    print("   Type 'exit' to quit.")
    print("="*50 + "\n")

    while True:
        # 2. Get User Input
        try:
            query = input("Search > ").strip()
        except KeyboardInterrupt:
            break
            
        if query.lower() in ['exit', 'quit']:
            break
        if not query:
            continue

        # 3. CALL THE LOGIC
        # This uses the complex logic we defined in search_service.py
        result = search_logic(query, db)

        # 4. DISPLAY RESULTS
        if result.get("status") == "no_match":
            print(f"❌ {result['message']}\n")
            continue

        # Print Header Info
        print(f"\n✅ Intent Parsed: {result.get('result_type', 'DERIVATIVES')}")
        print(f"   Underlying: {result.get('underlying')}")
        
        parsed = result.get('search_parsed', {})
        if parsed:
            expiry = parsed.get('expiry_month', '-') or '-'
            strike = parsed.get('strike', '-') or '-'
            print(f"   Filters: Exp[{expiry}] Strike[{strike}]")

        # Print The Matches Table
        matches = result.get("matches", [])
        
        if not matches:
            # Fallback for Equity/Index simple result
            if "data" in result:
                d = result["data"]
                print(f"\n   🎯 Found: {d['symbol']} ({d['type']})")
            else:
                print("   ⚠️ No specific instruments found matching criteria.")
        else:
            print(f"\n   {'SYMBOL':<25} {'TYPE':<10} {'DISPLAY NAME'}")
            print("   " + "-"*60)
            
            for m in matches:
                print(f"   {m['symbol']:<25} {m['type']:<10} {m['display_name']}")
        
        print("\n")

if __name__ == "__main__":
    run_interactive_tool()