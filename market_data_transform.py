import json

# 1. Load your original file
try:
    with open('symbol_info_list.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: Could not find 'symbol_info_list.json'. Make sure it is in the same folder.")
    exit()

# 2. Define the types we want (Equity, Index, Derivatives)
RELEVANT_TYPES = {1, 2, 3, 4, 5, 6}

processed_data = []

for row in data:
    itype = row[0]
    
    # Skip types we don't want (Mutual Funds, Gold Bonds, etc.)
    if itype not in RELEVANT_TYPES:
        continue

    # 3. Process Equity & Index (Types 1 & 2)
    if itype in [1, 2]:
        entry = {
            "InstrumentType": row[0],
            "Symbol": row[1],
            "InstrumentId": row[2],
            "DisplaySymbol": row[3],
            "Exchange": row[5],
            "Segment": row[11],
            "TradingSymbol": row[12],
            "Isin": row[14],
            "UnderlyingInstrumentId": None,
            "ExpiryDate": None,
            "ExpiryType": None,
            "OptionType": None,
            "StrikePrice": None
        }

    # 4. Process Derivatives (F&O - Types 3, 4, 5, 6)
    else:
        entry = {
            "InstrumentType": row[0],
            "Symbol": row[1],
            "InstrumentId": row[2],
            "DisplaySymbol": row[4],
            "Exchange": None, # Not provided in FO schema
            "Segment": row[13],
            "TradingSymbol": row[1],
            "Isin": None,
            "UnderlyingInstrumentId": row[3],
            "ExpiryDate": row[5],
            "ExpiryType": row[6],
            "OptionType": row[9],
            "StrikePrice": row[10]
        }
    
    processed_data.append(entry)

# 5. Save the clean file
output_file = 'processed_symbol_data.json'
with open(output_file, 'w') as f:
    json.dump(processed_data, f, indent=4)

print(f"Success! Created {output_file} with {len(processed_data)} entries.")