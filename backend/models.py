from sqlalchemy import Column, Integer, String, Float, Boolean
from backend.database import Base

class Zapas(Base):
    __tablename__ = "zapasy"

    id = Column(Integer, primary_key=True, index=True)
    domaci = Column(String)       # Napr. "Arsenal"
    hostia = Column(String)       # Napr. "Chelsea"
    kurz = Column(Float)          # Napr. 2.5
    sanca = Column(Float)         # Napr. 50.0
    je_to_value = Column(Boolean) # True/False