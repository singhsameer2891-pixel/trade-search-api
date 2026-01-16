# Search Service Logic - Exhaustive Rules Documentation

## Overview
The search service processes financial instrument queries and returns matching results from a database. It handles two main scenarios: **Pure Search** (symbol-only queries) and **Specific F&O Search** (queries with strike prices, expiry dates, option types, etc.).

---

## 1. QUERY PARSING RULES (`parse_query`)

### 1.1 Input Normalization
- **Rule 1.1.1**: Query is converted to UPPERCASE and stripped of leading/trailing whitespace
- **Rule 1.1.2**: All parsing operates on the normalized uppercase string

### 1.2 Strike Price Extraction
- **Rule 1.2.1**: Strike price can be specified in two formats:
  - **K-notation**: Pattern `\b(\d+(\.\d+)?)[kK]\b` (e.g., "24.5k", "25K")
    - Value is multiplied by 1000 (e.g., "24.5k" → 24500)
    - The matched text is removed from the query string
  - **Normal notation**: Pattern `\b(\d{4,6})\b` (4-6 digit numbers)
    - Value is used as-is (e.g., "24500" → 24500)
    - The matched text is removed from the query string

- **Rule 1.2.2**: K-notation takes precedence over normal notation if both match
- **Rule 1.2.3**: Only the first matching strike price is extracted
- **Rule 1.2.4**: If no strike price is found, `strike = None`

### 1.3 Expiry Day Extraction
- **Rule 1.3.1**: Pattern `\b(\d{1,2})\b` matches 1-2 digit numbers
- **Rule 1.3.2**: Only numbers between 1-31 (inclusive) are considered valid expiry days
- **Rule 1.3.3**: The first valid day match is used; subsequent matches are ignored
- **Rule 1.3.4**: The matched day text is replaced with a single space in the query
- **Rule 1.3.5**: If no valid day is found, `expiry_day = None`

### 1.4 Option Type Extraction
- **Rule 1.4.1**: Pattern `\b(CE|PE|CALL|PUT)\b` matches option type indicators
- **Rule 1.4.2**: Only the first match is used
- **Rule 1.4.3**: If no match, `opt_type = None`

### 1.5 Expiry Month Extraction
- **Rule 1.5.1**: Pattern `\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b` matches month abbreviations
- **Rule 1.5.2**: Only the first match is used
- **Rule 1.5.3**: If no match, `expiry_month = None`

### 1.6 Futures Tag Detection
- **Rule 1.6.1**: Pattern `\b(FUT|FUTURE|FUTURES)\b` detects futures keywords
- **Rule 1.6.2**: If any match is found, `is_future = True`, otherwise `False`

### 1.7 Text Cleanup
- **Rule 1.7.1**: After extracting all components, the query is cleaned:
  1. Remove option type text (if found)
  2. Remove expiry month text (if found)
  3. Remove futures tag text (if found)
  4. Remove all non-alphanumeric characters except spaces: `[^A-Z0-9\s]`
  5. Collapse multiple spaces into single spaces
  6. Strip leading/trailing whitespace

- **Rule 1.7.2**: The remaining text becomes `raw_symbol`

### 1.8 Return Value
- **Rule 1.8.1**: Returns a dictionary with:
  - `raw_symbol`: Cleaned symbol text (may be empty)
  - `strike`: Numeric strike price or `None`
  - `expiry_month`: Month abbreviation or `None`
  - `expiry_day`: Day number (1-31) or `None`
  - `opt_type`: Option type string or `None`
  - `is_future`: Boolean

---

## 2. DATE PARSING RULES (`parse_date`)

### 2.1 Input Handling
- **Rule 2.1.1**: If `date_str` is `None` or empty, returns `datetime.max`
- **Rule 2.1.2**: Attempts to parse using format `"%d-%b-%y"` (e.g., "27-Jan-25")
- **Rule 2.1.3**: If parsing fails, returns `datetime.max`
- **Rule 2.1.4**: `datetime.max` is used as a sentinel value for sorting (invalid dates sort last)

---

## 3. FUTURES RETRIEVAL RULES (`get_futures_by_id`)

### 3.1 Query Construction
- **Rule 3.1.1**: Queries instruments where:
  - `UnderlyingInstrumentId == underlying_id` (exact match)
  - `InstrumentType` is in `[4, 6]` (futures types)

### 3.2 Sorting
- **Rule 3.2.1**: Results are sorted by expiry date (ascending) using `parse_date`
- **Rule 3.2.2**: Instruments with invalid/missing dates sort last

### 3.3 Result Limiting
- **Rule 3.3.1**: Returns only the first 3 futures (nearest expiry dates)

---

## 4. SYMBOL RESOLUTION RULES (`resolve_symbol`)

### 4.1 Input Validation
- **Rule 4.1.1**: If `symbol_text` is empty/None, returns `(None, False)`

### 4.2 Resolution Hierarchy (Strict Order)

#### 4.2.1 Exact Match (Priority 1)
- **Rule 4.2.1.1**: Queries for instruments where:
  - `Symbol == symbol_text` (case-sensitive after normalization)
  - `InstrumentType` is in `[1, 2]` (equity/index types)

- **Rule 4.2.1.2**: If exactly one match found:
  - Returns `(match, False)` where `False` indicates no typo fix

- **Rule 4.2.1.3**: If multiple exact matches found (e.g., BSE vs NSE):
  - **Priority 1**: If any match has `InstrumentType == 2` (INDEX), return that one
  - **Priority 2**: Check which candidate has derivatives (children):
    - Query for instruments where `UnderlyingInstrumentId == candidate.InstrumentId`
    - If found, that candidate is the "parent" and is returned
  - **Priority 3**: If no derivatives found, return the first match
  - Returns `(best_candidate, False)`

#### 4.2.2 Prefix Match (Priority 2)
- **Rule 4.2.2.1**: Only executed if exact match fails
- **Rule 4.2.2.2**: Queries for instruments where:
  - `Symbol LIKE 'symbol_text%'` (starts with symbol_text)
  - `InstrumentType` is in `[1, 2]`

- **Rule 4.2.2.3**: If candidates found:
  - Sorted by: `(len(Symbol), Symbol)` (shortest first, then alphabetical)
  - Returns `(first_candidate, False)`

- **Rule 4.2.2.4**: This prevents "NIFTY" from matching "NIFTY DIV OPPS 50" when "NIFTY" exists

#### 4.2.3 Fuzzy Match (Priority 3)
- **Rule 4.2.3.1**: Only executed if exact and prefix matches fail
- **Rule 4.2.3.2**: Fetches all distinct symbols with `InstrumentType` in `[1, 2]`
- **Rule 4.2.3.3**: Uses `thefuzz.process.extractOne` with `fuzz.ratio` scorer
- **Rule 4.2.3.4**: Only accepts matches with score >= 80
- **Rule 4.2.3.5**: If match found, queries for the instrument and returns `(match, True)` where `True` indicates typo was fixed
- **Rule 4.2.3.6**: If no match or score < 80, returns `(None, False)`

---

## 5. STRIKE DISTANCE CALCULATION (`calculate_distance`)

### 5.1 Input Handling
- **Rule 5.1.1**: If `target_strike` is `None`, returns `0`
- **Rule 5.1.2**: If `inst.StrikePrice` is `None`, returns `99999999` (very large penalty)

### 5.2 Scale Normalization
- **Rule 5.2.1**: Database may store strikes in two scales:
  - Normal scale: e.g., 24500
  - x100 scale: e.g., 2450000 (for some instruments)

- **Rule 5.2.2**: If `db_strike > target_strike * 5`, assumes x100 scale and divides by 100
- **Rule 5.2.3**: Calculates absolute difference: `abs(normalized_db_strike - target_strike)`

### 5.3 Return Value
- **Rule 5.3.1**: Returns non-negative integer representing distance from target

---

## 6. INSTRUMENT RANKING RULES (`get_instrument_rank`)

### 6.1 Purpose
- **Rule 6.1.1**: Assigns numeric rank for sorting (lower = higher priority)
- **Rule 6.1.2**: Structure: Indices (10-40) → Stocks (50+)
- **Rule 6.1.3**: Within each category: Futures < Options (e.g., 10 < 11)

### 6.2 Ranking Hierarchy

#### 6.2.1 NIFTY
- **Rule 6.2.1.1**: If symbol starts with "NIFTY" AND does NOT start with "NIFTYNXT" AND does NOT start with "NIFTYMID":
  - Futures (types 4, 6): rank = 10
  - Options (types 3, 5): rank = 11

#### 6.2.2 BANKNIFTY
- **Rule 6.2.2.1**: If symbol starts with "BANKNIFTY":
  - Futures: rank = 20
  - Options: rank = 21

#### 6.2.3 FINNIFTY
- **Rule 6.2.3.1**: If symbol starts with "FINNIFTY":
  - Futures: rank = 30
  - Options: rank = 31

#### 6.2.4 Other Indices
- **Rule 6.2.4.1**: If `InstrumentType` is in `[5, 6]` (index options/futures):
  - Futures: rank = 40
  - Options: rank = 41

#### 6.2.5 Stocks
- **Rule 6.2.5.1**: All other instruments:
  - Futures: rank = 50
  - Options: rank = 51

---

## 7. MAIN SEARCH LOGIC (`search_logic`)

### 7.1 Initial Processing
- **Rule 7.1.1**: Calls `parse_query(query)` to extract components
- **Rule 7.1.2**: Calls `resolve_symbol(parsed["raw_symbol"], db)` to find underlying
- **Rule 7.1.3**: Returns tuple `(hero, is_typo_fixed)` from symbol resolution

### 7.2 Pure Search Detection
- **Rule 7.2.1**: A query is "pure search" if ALL of the following are falsy:
  - `strike`
  - `parsed["is_future"]`
  - `parsed["opt_type"]`
  - `parsed["expiry_month"]`
  - `parsed["expiry_day"]`

- **Rule 7.2.2**: Pure search examples: "NIFTY", "Reliance", "BANKNIFTY"
- **Rule 7.2.3**: Non-pure search examples: "NIFTY 24500", "NIFTY JAN", "NIFTY CE"

---

## 8. SCENARIO 1: PURE SEARCH RULES

### 8.1 Result Collection
- **Rule 8.1.1**: Maintains a `seen_ids` set to prevent duplicate results
- **Rule 8.1.2**: Results list is built incrementally

### 8.2 Hero Match (Priority 1)
- **Rule 8.2.1**: If `hero` is found:
  - Adds result with:
    - `display_name`: `hero.DisplaySymbol` or `hero.Symbol` (fallback)
    - `symbol`: `hero.Symbol`
    - `type`: "INDEX" if `hero.InstrumentType == 2`, else "EQUITY"
    - `priority`: 1
  - Adds `hero.InstrumentId` to `seen_ids`

### 8.3 Hero Futures (Priority 2)
- **Rule 8.3.1**: If `hero` exists, calls `get_futures_by_id(hero.InstrumentId, db)`
- **Rule 8.3.2**: For each future (up to 3):
  - Adds result with:
    - `display_name`: `f.DisplaySymbol`
    - `symbol`: `f.Symbol`
    - `type`: "FUT"
    - `priority`: 2

### 8.4 Partial Matches (Priority 3)
- **Rule 8.4.1**: Only executed if `is_typo_fixed == False`
- **Rule 8.4.2**: If typo was fixed via fuzzy match, partials are NOT shown (prevents confusion)
- **Rule 8.4.3**: Queries for instruments where:
  - `Symbol LIKE 'symbol_text%'`
  - `InstrumentType` in `[1, 2]`
- **Rule 8.4.4**: Results ordered by `Symbol` (ascending), limited to 10
- **Rule 8.4.5**: For each partial:
  - Skips if `InstrumentId` already in `seen_ids`
  - Adds result with:
    - `display_name`: `p.DisplaySymbol` or `p.Symbol`
    - `symbol`: `p.Symbol`
    - `type`: "INDEX" if `p.InstrumentType == 2`, else "EQUITY"
    - `priority`: 3
  - Adds `p.InstrumentId` to `seen_ids`

### 8.5 Sorting and Return
- **Rule 8.5.1**: Results sorted by `priority` (ascending): 1 → 2 → 3
- **Rule 8.5.2**: If no results, returns:
  ```json
  {
    "status": "no_match",
    "message": "No symbol found matching '{symbol_text}'"
  }
  ```
- **Rule 8.5.3**: If results found, returns:
  ```json
  {
    "status": "success",
    "result_type": "UNIVERSAL_SEARCH",
    "underlying": symbol_text,
    "is_typo_fixed": is_typo_fixed,
    "matches": [/* sorted results */]
  }
  ```

---

## 9. SCENARIO 2: SPECIFIC F&O / GLOBAL SEARCH RULES

### 9.1 Underlying Resolution
- **Rule 9.1.1**: Uses `hero` from symbol resolution as `underlying_obj`
- **Rule 9.1.2**: If `underlying_obj` is `None`, the search becomes "GLOBAL SEARCH" (no underlying filter)

### 9.2 Query Filter Construction

#### 9.2.1 Underlying Filter
- **Rule 9.2.1.1**: If `underlying_obj` exists:
  - Adds filter: `UnderlyingInstrumentId == underlying_obj.InstrumentId`
- **Rule 9.2.1.2**: If `underlying_obj` is `None`, no underlying filter is applied

#### 9.2.2 Instrument Type Filter
- **Rule 9.2.2.1**: If `parsed["is_future"] == True`:
  - Adds filter: `InstrumentType` in `[4, 6]` (futures)

- **Rule 9.2.2.2**: Else if `strike` is not None:
  - Adds filter: `InstrumentType` in `[3, 5]` (options)

- **Rule 9.2.2.3**: Else if `parsed["expiry_day"]` is not None:
  - Adds filter: `InstrumentType` in `[3, 4, 5, 6]` (all F&O)

- **Rule 9.2.2.4**: Else (default case):
  - If `parsed["opt_type"]` exists:
    - Adds filter: `InstrumentType` in `[3, 5]` (options)
    - Adds filter: `DisplaySymbol LIKE '%opt_type%'`
  - Else:
    - Adds filter: `InstrumentType` in `[4, 6]` (futures)

#### 9.2.3 Date Filters
- **Rule 9.2.3.1**: If `parsed["expiry_month"]` exists:
  - Adds filter: `ExpiryDate LIKE '%expiry_month%'` (e.g., "JAN")

- **Rule 9.2.3.2**: If `parsed["expiry_day"]` exists:
  - Adds filter: `ExpiryDate LIKE 'DD-%'` where DD is zero-padded (e.g., "27-%")

### 9.3 Strike Price Query Execution

#### 9.3.1 Strict Match (First Attempt)
- **Rule 9.3.1.1**: If `strike` is not None:
  - Creates `strict_filters` copy of `query_filters`
  - Adds filter: `StrikePrice == strike OR StrikePrice == strike * 100`
  - If `parsed["opt_type"]` exists, adds: `DisplaySymbol LIKE '%opt_type%'`
  - Executes query with limit 50000
  - If results found, uses these as `final_results`

#### 9.3.2 Range Match (Fallback)
- **Rule 9.3.2.1**: Only executed if strict match returns no results
- **Rule 9.3.2.2**: Creates `range_filters` copy of `query_filters`
- **Rule 9.3.2.3**: Calculates range windows:
  - Normal scale: `[strike * 0.95, strike * 1.05]` (±5%)
  - x100 scale: `[(strike * 100) * 0.95, (strike * 100) * 1.05]`
- **Rule 9.3.2.4**: Adds filter:
  ```
  (StrikePrice >= min_s AND StrikePrice <= max_s)
  OR
  (StrikePrice >= min_s_100 AND StrikePrice <= max_s_100)
  ```
- **Rule 9.3.2.5**: If `parsed["opt_type"]` exists, adds: `DisplaySymbol LIKE '%opt_type%'`
- **Rule 9.3.2.6**: Executes query with limit 50000
- **Rule 9.3.2.7**: Results are sorted by distance from target strike (see Rule 9.4.3)

#### 9.3.3 Non-Strike Query
- **Rule 9.3.3.1**: If `strike` is None:
  - Executes query with all `query_filters` and limit 50000
  - Results stored as `final_results`

### 9.4 Result Formatting and Sorting

#### 9.4.1 SPOT Entry
- **Rule 9.4.1.1**: If `underlying_obj` exists:
  - Adds SPOT entry at the beginning with:
    - `display_name`: `underlying_obj.DisplaySymbol`
    - `symbol`: `underlying_obj.Symbol`
    - `type`: "SPOT"
    - Temporary sort fields: `expiry_sort = datetime.min`, `dist_score = 0`, `strike_val = 0`, `rank = 0`

#### 9.4.2 F&O Entry Formatting
- **Rule 9.4.2.1**: For each result in `final_results`:
  - Creates entry with:
    - `display_name`: `res.DisplaySymbol`
    - `symbol`: `res.Symbol`
    - `type`: "FUT" if `res.InstrumentType` in `[4, 6]`, else "OPT"
    - `expiry_sort`: `parse_date(res.ExpiryDate)`
    - `dist_score`: `calculate_distance(res, strike)`
    - `strike_val`: `res.StrikePrice` or `0`
    - `rank`: `get_instrument_rank(res)`

#### 9.4.3 Sorting Logic
- **Rule 9.4.3.1**: Results sorted by tuple: `(rank, expiry_sort, dist_score, strike_val)`
  - `rank`: Lower is better (NIFTY=10, BANKNIFTY=20, etc.)
  - `expiry_sort`: Earlier dates first (`datetime.min` sorts first)
  - `dist_score`: Closer to target strike first (0 is best)
  - `strike_val`: Lower strikes first (for generic searches)

- **Rule 9.4.3.2**: For range match results (Rule 9.3.2), Python-side sorting by distance happens before this step

#### 9.4.4 Result Limiting
- **Rule 9.4.4.1**: Takes top 10 entries from sorted list (after SPOT entry)
- **Rule 9.4.4.2**: Removes temporary sort fields: `expiry_sort`, `dist_score`, `strike_val`, `rank`

### 9.5 Return Value
- **Rule 9.5.1**: Returns:
  ```json
  {
    "status": "success",
    "search_parsed": parsed,
    "underlying": underlying_obj.Symbol if underlying_obj else "GLOBAL_SEARCH",
    "is_typo_fixed": is_typo_fixed,
    "matches": [/* formatted_results */]
  }
  ```

---

## 10. INSTRUMENT TYPE MAPPING

### 10.1 Database Types
- **Rule 10.1.1**: `InstrumentType` values:
  - `1`: Equity (Stock)
  - `2`: Index
  - `3`: Stock Option
  - `4`: Stock Future
  - `5`: Index Option
  - `6`: Index Future

### 10.2 Result Type Mapping
- **Rule 10.2.1**: Result `type` field values:
  - "EQUITY": `InstrumentType == 1`
  - "INDEX": `InstrumentType == 2`
  - "SPOT": Underlying instrument (always type 1 or 2)
  - "FUT": `InstrumentType` in `[4, 6]`
  - "OPT": `InstrumentType` in `[3, 5]`

---

## 11. EDGE CASES AND SPECIAL BEHAVIORS

### 11.1 Empty Query
- **Rule 11.1.1**: If query is empty/whitespace after normalization:
  - `raw_symbol` will be empty string
  - `resolve_symbol("", db)` returns `(None, False)`
  - Pure search returns no results
  - F&O search fails (no underlying)

### 11.2 Symbol with No Derivatives
- **Rule 11.2.1**: If symbol exists but has no futures/options:
  - Pure search shows symbol + no futures
  - F&O search with that symbol returns only SPOT entry

### 11.3 Invalid Strike Prices
- **Rule 11.3.1**: If user enters invalid strike (e.g., "24560" when only 24500/24600 exist):
  - Strict match returns empty
  - Range match (±5%) finds nearest valid strikes
  - Results sorted by distance from target

### 11.4 Multiple Underlying Matches
- **Rule 11.4.1**: Handled in `resolve_symbol` (Rule 4.2.1.3):
  - Prefers INDEX type
  - Then prefers instrument with derivatives
  - Falls back to first match

### 11.5 Typo Correction
- **Rule 11.5.1**: If fuzzy match corrects typo (`is_typo_fixed == True`):
  - Pure search does NOT show partial matches
  - Prevents showing "NIFTY 50" when user typed "NIFTI"

### 11.6 Global Search (No Underlying)
- **Rule 11.6.1**: If symbol resolution fails but query has date/strike:
  - Search becomes "GLOBAL_SEARCH"
  - No `UnderlyingInstrumentId` filter applied
  - Results from all underlyings matching other criteria

### 11.7 Date Parsing Failures
- **Rule 11.7.1**: Invalid dates parse to `datetime.max`
- **Rule 11.7.2**: Instruments with `datetime.max` sort last in expiry-based sorting

### 11.8 Strike Scale Ambiguity
- **Rule 11.8.1**: Database may store strikes in two scales
- **Rule 11.8.2**: Query checks both: `strike` and `strike * 100`
- **Rule 11.8.3**: Distance calculation normalizes x100 scale for comparison

---

## 12. PERFORMANCE CONSIDERATIONS

### 12.1 Query Limits
- **Rule 12.1.1**: F&O queries fetch up to 50000 results for Python-side sorting
- **Rule 12.1.2**: Final results limited to 10 entries
- **Rule 12.1.3**: Pure search partials limited to 10

### 12.2 Sorting Strategy
- **Rule 12.2.1**: Database queries use SQL `ORDER BY` where possible
- **Rule 12.2.2**: Complex multi-criteria sorting done in Python after fetching
- **Rule 12.2.3**: Range match results sorted by distance in Python before final sort

---

## 13. SUMMARY OF KEY DECISIONS

1. **Strike Matching**: Tries exact match first, falls back to ±5% range search
2. **Symbol Resolution**: Exact → Prefix → Fuzzy (80% threshold)
3. **Duplicate Prevention**: Uses `seen_ids` set in pure search
4. **Typo Handling**: Fuzzy matches disable partial results to avoid confusion
5. **Ranking**: NIFTY < BANKNIFTY < FINNIFTY < Other Indices < Stocks
6. **Futures Priority**: Futures rank lower (better) than Options within same category
7. **Scale Handling**: Supports both normal and x100 strike scales
8. **Global Search**: Allows date/strike queries without underlying symbol
9. **Result Limiting**: Always returns max 10 F&O results + 1 SPOT
10. **Date Handling**: Invalid dates sort last using `datetime.max` sentinel

---

## 14. TESTING SCENARIOS

### 14.1 Pure Search Examples
- "NIFTY" → Hero + 3 nearest futures + partials (if not typo-fixed)
- "Reliance" → Hero + futures + partials
- "NIFTI" → Fuzzy match to "NIFTY", no partials

### 14.2 F&O Search Examples
- "NIFTY 24500" → Options with strike 24500 or 2450000
- "NIFTY 24560" → Range search, sorted by distance
- "NIFTY JAN" → Futures expiring in January
- "NIFTY 27 JAN" → F&O expiring on 27th of January
- "NIFTY CE" → All NIFTY call options
- "27 JAN" → Global search, all instruments expiring 27 Jan

### 14.3 Edge Cases
- "24500" → Global search with strike, defaults to NIFTY if no symbol
- "NIFTY FUT" → NIFTY futures only
- "DIXON" → Resolves to parent with derivatives (if multiple exist)

---

**End of Rules Documentation**

