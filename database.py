from sqlalchemy import create_engine, Column, String, Integer, Float, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Database Connection
SQLALCHEMY_DATABASE_URL = "sqlite:///./market.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 2. Define the "Instrument" Table
class Instrument(Base):
    __tablename__ = "instruments"

    InstrumentId = Column(BigInteger, primary_key=True, index=True)
    InstrumentType = Column(Integer)
    Symbol = Column(String, index=True) 
    DisplaySymbol = Column(String)
    Exchange = Column(Integer, nullable=True)
    Segment = Column(Integer)
    TradingSymbol = Column(String)
    Isin = Column(String, nullable=True)
    UnderlyingInstrumentId = Column(BigInteger, nullable=True)
    ExpiryDate = Column(String, nullable=True)
    ExpiryType = Column(Integer, nullable=True)
    OptionType = Column(Integer, nullable=True)
    StrikePrice = Column(Float, nullable=True)

# 3. Create Tables Helper (Safe)
# This only creates tables if they DO NOT exist. It won't delete anything.
def create_tables():
    Base.metadata.create_all(bind=engine)

# 4. Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()