import re
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from ..database import Instrument
from thefuzz import process, fuzz

# --- CONSTANTS ---
MONTHS = r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b"
OPTION_TYPES = r"\b(CE|PE|CALL|PUT)\b"
FUTURES_TAGS = r"\b(FUT|FUTURE|FUTURES)\b"
STRIKE_K_NOTATION = r"\b(\d+(\.\d+)?)[kK]\b" 
STRIKE_NORMAL = r"\b(\d{4,6})\b"
EXPIRY_DAY = r"\b(\d{1,2})\b"

def parse_query(query: str):
    q_upper = query.upper().strip()
    
    # 1. Strike Price
    strike = None
    k_match = re.search(STRIKE_K_NOTATION, q_upper)
    if k_match:
        val = float(k_match.group(1))
        strike = val * 1000
        q_upper = q_upper.replace(k_match.group(0), "")
    else:
        s_match = re.search(STRIKE_NORMAL, q_upper)
        if s_match:
            strike = float(s_match.group(1))
            q_upper = q_upper.replace(s_match.group(0), "")

    # 2. Expiry Day
    expiry_day = None
    day_matches = re.finditer(EXPIRY_DAY, q_upper)
    for m in day_matches:
        val = int(m.group(1))
        if 1 <= val <= 31:
            expiry_day = val
            q_upper = q_upper.replace(m.group(0), " ", 1) 
            break

    # 3. Other Tags
    opt_match = re.search(OPTION_TYPES, q_upper)
    opt_type = opt_match.group(1) if opt_match else None
    
    exp_match = re.search(MONTHS, q_upper)
    expiry_month = exp_match.group(1) if exp_match else None
    
    is_future = re.search(FUTURES_TAGS, q_upper) is not None
    
    # 4. Cleanup
    clean_text = q_upper
    if opt_type: clean_text = re.sub(OPTION_TYPES, "", clean_text)
    if expiry_month: clean_text = re.sub(MONTHS, "", clean_text)
    if is_future: clean_text = re.sub(FUTURES_TAGS, "", clean_text)
    
    symbol_text = re.sub(r'[^A-Z0-9\s]', '', clean_text).strip()
    symbol_text = re.sub(r'\s+', ' ', symbol_text)

    return {
        "raw_symbol": symbol_text,
        "strike": strike,
        "expiry_month": expiry_month,
        "expiry_day": expiry_day,
        "opt_type": opt_type,
        "is_future": is_future
    }

def parse_date(date_str):
    if not date_str: return datetime.max
    try:
        return datetime.strptime(date_str, "%d-%b-%y")
    except:
        return datetime.max

def get_futures_by_id(underlying_id: int, db: Session):
    futs = db.query(Instrument).filter(
        Instrument.UnderlyingInstrumentId == underlying_id,
        Instrument.InstrumentType.in_([4, 6])
    ).all()
    futs.sort(key=lambda x: parse_date(x.ExpiryDate))
    return futs[:3]

def resolve_symbol(symbol_text: str, db: Session):
    """
    Identifies the correct underlying instrument.
    Fixes the 'Twin Problem' (BSE vs NSE) by checking which one actually has derivatives.
    """
    if not symbol_text: return None, False

    # 1. Exact Match
    exact_matches = db.query(Instrument).filter(
        Instrument.Symbol == symbol_text,
        Instrument.InstrumentType.in_([1, 2])
    ).all()
    
    if exact_matches:
        # If we found multiple "DIXON"s, we need to find the "Parent"
        if len(exact_matches) > 1:
            best_candidate = exact_matches[0] # Default to first
            
            for cand in exact_matches:
                # Priority 1: Indices are always masters
                if cand.InstrumentType == 2:
                    return cand, False
                
                # Priority 2: Check if this candidate acts as a parent
                # We query for just ONE child to confirm parentage
                has_child = db.query(Instrument.InstrumentId).filter(
                    Instrument.UnderlyingInstrumentId == cand.InstrumentId
                ).first()
                
                if has_child:
                    return cand, False
            
            # If no derivatives found for any, default to the first one
            return best_candidate, False
        else:
            return exact_matches[0], False

    # 2. Prefix Match
    candidates = db.query(Instrument).filter(
        Instrument.Symbol.like(f"{symbol_text}%"),
        Instrument.InstrumentType.in_([1, 2])
    ).all()
    if candidates:
        candidates.sort(key=lambda x: (len(x.Symbol), x.Symbol))
        return candidates[0], False

    # 3. Fuzzy Match
    all_symbols = db.query(Instrument.Symbol).filter(
        Instrument.InstrumentType.in_([1, 2])
    ).distinct().all()
    choices = [s[0] for s in all_symbols]
    match, score = process.extractOne(symbol_text, choices, scorer=fuzz.ratio)
    
    if score >= 80:
        fuzzy_hero = db.query(Instrument).filter(
            Instrument.Symbol == match,
            Instrument.InstrumentType.in_([1, 2])
        ).first()
        return fuzzy_hero, True

    return None, False

def calculate_distance(inst, target_strike):
    if target_strike is None: return 0
    if not inst.StrikePrice: return 99999999
    
    db_strike = inst.StrikePrice
    if db_strike > target_strike * 5:
        db_strike = db_strike / 100
        
    return abs(db_strike - target_strike)

def get_instrument_rank(inst):
    sym = inst.Symbol.upper()
    is_future = inst.InstrumentType in [4, 6]
    
    if sym.startswith("NIFTY") and not sym.startswith("NIFTYNXT") and not sym.startswith("NIFTYMID"):
        return 10 if is_future else 11
    if sym.startswith("BANKNIFTY"):
        return 20 if is_future else 21
    if sym.startswith("FINNIFTY"):
        return 30 if is_future else 31
    if inst.InstrumentType in [5, 6]:
        return 40 if is_future else 41
    return 50 if is_future else 51

def search_logic(query: str, db: Session):
    parsed = parse_query(query)
    
    symbol_text = parsed["raw_symbol"]
    strike = parsed["strike"]
    
    is_pure_search = not (
        strike or 
        parsed["is_future"] or 
        parsed["opt_type"] or 
        parsed["expiry_month"] or 
        parsed["expiry_day"]
    )

    hero, is_typo_fixed = resolve_symbol(symbol_text, db)

    # ==========================================================
    # SCENARIO 1: PURE SEARCH
    # ==========================================================
    if is_pure_search:
        results = []
        seen_ids = set()

        if hero:
            results.append({
                "display_name": hero.DisplaySymbol or hero.Symbol,
                "symbol": hero.Symbol,
                "type": "INDEX" if hero.InstrumentType == 2 else "EQUITY",
                "priority": 1
            })
            seen_ids.add(hero.InstrumentId)

            futures = get_futures_by_id(hero.InstrumentId, db)
            for f in futures:
                results.append({
                    "display_name": f.DisplaySymbol,
                    "symbol": f.Symbol,
                    "type": "FUT",
                    "priority": 2
                })

        if not is_typo_fixed:
            partials = db.query(Instrument).filter(
                Instrument.Symbol.like(f"{symbol_text}%"),
                Instrument.InstrumentType.in_([1, 2])
            ).order_by(Instrument.Symbol.asc()).limit(10).all()

            for p in partials:
                if p.InstrumentId not in seen_ids:
                    results.append({
                        "display_name": p.DisplaySymbol or p.Symbol,
                        "symbol": p.Symbol,
                        "type": "INDEX" if p.InstrumentType == 2 else "EQUITY",
                        "priority": 3
                    })
                    seen_ids.add(p.InstrumentId)

        results.sort(key=lambda x: x['priority'])

        if not results:
             return {"status": "no_match", "message": f"No symbol found matching '{symbol_text}'"}

        return {
            "status": "success",
            "result_type": "UNIVERSAL_SEARCH",
            "underlying": symbol_text,
            "is_typo_fixed": is_typo_fixed,
            "matches": results
        }

    # ==========================================================
    # SCENARIO 2: SPECIFIC F&O / GLOBAL SEARCH
    # ==========================================================
    
    underlying_obj = hero
    
    query_filters = []
    
    if underlying_obj:
        query_filters.append(Instrument.UnderlyingInstrumentId == underlying_obj.InstrumentId)
    
    if parsed["is_future"]:
        query_filters.append(Instrument.InstrumentType.in_([4, 6]))
    elif strike:
        query_filters.append(Instrument.InstrumentType.in_([3, 5]))
    elif parsed["expiry_day"]:
        query_filters.append(Instrument.InstrumentType.in_([3, 4, 5, 6]))
    else:
        if parsed["opt_type"]:
             query_filters.append(Instrument.InstrumentType.in_([3, 5]))
             query_filters.append(Instrument.DisplaySymbol.like(f"%{parsed['opt_type']}%"))
        else:
             query_filters.append(Instrument.InstrumentType.in_([4, 6]))

    if parsed["expiry_month"]:
        query_filters.append(Instrument.ExpiryDate.like(f"%{parsed['expiry_month']}%"))
    if parsed["expiry_day"]:
        query_filters.append(Instrument.ExpiryDate.like(f"{parsed['expiry_day']:02d}-%"))

    # --- EXECUTE ---
    final_results = []
    
    if strike:
        strict_filters = query_filters.copy()
        strict_filters.append(or_(
            Instrument.StrikePrice == strike,
            Instrument.StrikePrice == strike * 100
        ))
        if parsed["opt_type"]:
             strict_filters.append(Instrument.DisplaySymbol.like(f"%{parsed['opt_type']}%"))
             
        final_results = db.query(Instrument).filter(and_(*strict_filters)).limit(50000).all()

        if not final_results:
            range_filters = query_filters.copy()
            min_s, max_s = strike * 0.95, strike * 1.05
            min_s_100, max_s_100 = (strike * 100) * 0.95, (strike * 100) * 1.05
            
            range_filters.append(or_(
                and_(Instrument.StrikePrice >= min_s, Instrument.StrikePrice <= max_s),
                and_(Instrument.StrikePrice >= min_s_100, Instrument.StrikePrice <= max_s_100)
            ))
            
            if parsed["opt_type"]:
                range_filters.append(Instrument.DisplaySymbol.like(f"%{parsed['opt_type']}%"))

            final_results = db.query(Instrument).filter(and_(*range_filters)).limit(50000).all()
    else:
        final_results = db.query(Instrument).filter(and_(*query_filters)).limit(50000).all()

    # --- FORMATTING & SORTING ---
    formatted_results = []
    
    if underlying_obj:
        formatted_results.append({
            "display_name": underlying_obj.DisplaySymbol,
            "symbol": underlying_obj.Symbol,
            "type": "SPOT",
            "expiry_sort": datetime.min,
            "dist_score": 0,
            "strike_val": 0,
            "rank": 0
        })

    temp_list = []
    for res in final_results:
        temp_list.append({
            "display_name": res.DisplaySymbol,
            "symbol": res.Symbol,
            "type": "FUT" if res.InstrumentType in [4,6] else "OPT",
            "expiry_sort": parse_date(res.ExpiryDate),
            "dist_score": calculate_distance(res, strike),
            "strike_val": res.StrikePrice if res.StrikePrice else 0,
            "rank": get_instrument_rank(res)
        })
        
    temp_list.sort(key=lambda x: (x["rank"], x["expiry_sort"], x["dist_score"], x["strike_val"]))
    
    formatted_results.extend(temp_list[:10])
    
    for item in formatted_results:
        item.pop("expiry_sort", None)
        item.pop("dist_score", None)
        item.pop("strike_val", None)
        item.pop("rank", None)
        
    return {
        "status": "success",
        "search_parsed": parsed,
        "underlying": underlying_obj.Symbol if underlying_obj else "GLOBAL_SEARCH",
        "is_typo_fixed": is_typo_fixed,
        "matches": formatted_results
    }