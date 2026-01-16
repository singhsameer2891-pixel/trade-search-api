from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal
from .services.search_service import search_logic

# 1. Initialize the App
app = FastAPI(title="Trade Search API")

# 2. Database Dependency (Opens/Closes DB for each request)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Define the Search Endpoint
@app.get("/search")
def search_endpoint(q: str, db: Session = Depends(get_db)):
    """
    Search for instruments using smart logic.
    Example: /search?q=Nifty 27 Jan
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query string 'q' cannot be empty")
    
    try:
        # Call your existing logic
        result = search_logic(q, db)
        return result
    except Exception as e:
        # Log the error internally and return a 500
        print(f"Server Error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))

# 4. Root Endpoint (Health Check)
@app.get("/")
def root():
    return {"message": "Trade Search API is running. Go to /search?q=nifty"}