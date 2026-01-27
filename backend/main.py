from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel

# Vytvorenie databázy
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Pomocná funkcia pre databázu
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Tvoje pôvodné funkcie ---

@app.get("/")
def home():
    return {"message": "Vitaj! Systém beží."}

@app.get("/zapasy")
def citat_zapasy(db: Session = Depends(get_db)):
    return crud.get_vsetky_zapasy(db)

@app.get("/analyzuj/{zapas_id}")
def spytat_sa_ai(zapas_id: int, db: Session = Depends(get_db)):
    # 1. Nájdeme zápas
    zapas = db.query(models.Zapas).filter(models.Zapas.id == zapas_id).first()
    
    if not zapas:
        return {"chyba": "Zápas s týmto ID neexistuje."}
    
    # 2. Pošleme ho do AI
    nazor_ai = ai.analyzuj_zapas_cez_ai(
        domaci=zapas.domaci,
        hostia=zapas.hostia,
        kurz=zapas.kurz,
        sanca=zapas.sanca
    )
    
    return {
        "zapas": f"{zapas.domaci} vs {zapas.hostia}",
        "AI_Analytik_Hovori": nazor_ai
    }

# --- NOVÉ DVERE PRE WHOP (Musí to byť takto pekne oddelené) ---

class WhopInput(BaseModel):
    message: str
    user_id: str | None = None

@app.post("/whop")
def komunikacia_s_whop(data: WhopInput):
    print(f"Whop poslal správu: {data.message}")
    
    # Testovacia odpoveď
    odpoved = f"Ahoj! Som tvoj Robot na Rendere. Píšeš mi: '{data.message}'. Systém funguje!"
    
    return {
        "response_message": odpoved
    }