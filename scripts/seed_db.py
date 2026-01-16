import json
import time
import sys
import os
from sqlalchemy.orm import Session

# Add parent directory to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Instrument, create_tables

def seed_database():
    db = SessionLocal()
    
    # 1. ENSURE TABLE EXISTS
    # If the table is missing, this creates it. If it exists, this does nothing.
    create_tables()

    # 2. CLEAR EXISTING DATA (The "Delete *" logic)
    print("🗑️  Clearing all data from 'instruments' table...")
    try:
        # This is equivalent to SQL: DELETE FROM instruments;
        rows_deleted = db.query(Instrument).delete()
        db.commit() # <--- COMMIT IS CRUCIAL! This saves the empty state.
        print(f"✅ Wiped {rows_deleted} old rows. Table is now empty.")
    except Exception as e:
        print(f"❌ Error deleting rows: {e}")
        db.rollback()
        return

    # 3. LOAD JSON DATA
    import os
    json_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed_symbol_data.json")
    print(f"📂 Reading {json_file}...")
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {json_file} not found.")
        return

    print(f"⚙️  Preparing {len(data)} records for insertion...")
    
    instruments_to_insert = []
    
    for entry in data:
        inst = Instrument(
            InstrumentType=entry.get('InstrumentType'),
            Symbol=entry.get('Symbol'),
            InstrumentId=entry.get('InstrumentId'),
            DisplaySymbol=entry.get('DisplaySymbol'),
            Exchange=entry.get('Exchange'),
            Segment=entry.get('Segment'),
            TradingSymbol=entry.get('TradingSymbol'),
            Isin=entry.get('Isin'),
            UnderlyingInstrumentId=entry.get('UnderlyingInstrumentId'),
            ExpiryDate=entry.get('ExpiryDate'),
            ExpiryType=entry.get('ExpiryType'),
            OptionType=entry.get('OptionType'),
            StrikePrice=entry.get('StrikePrice')
        )
        instruments_to_insert.append(inst)

    # 4. INSERT NEW DATA
    print("🚀 Inserting data into SQLite...")
    start_time = time.time()
    
    try:
        db.bulk_save_objects(instruments_to_insert)
        db.commit() # Save the new rows
        end_time = time.time()
        print(f"✅ Success! Inserted {len(instruments_to_insert)} records in {end_time - start_time:.2f} seconds.")
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()