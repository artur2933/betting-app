from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from backend import models, crud, database, ai # <--- PRIDAL SOM 'ai'

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message": "Vitaj! Systém beží."}

@app.get("/zapasy")
def citat_zapasy(db: Session = Depends(get_db)):
    return crud.get_vsetky_zapasy(db)

# --- NOVÉ TLAČIDLO PRE AI ---
@app.get("/analyzuj/{zapas_id}")
def spytat_sa_ai(zapas_id: int, db: Session = Depends(get_db)):
    # 1. Nájdeme zápas v databáze
    zapas = db.query(models.Zapas).filter(models.Zapas.id == zapas_id).first()
    
    if not zapas:
        return {"chyba": "Zápas s týmto ID neexistuje."}
    
    # 2. Pošleme ho do AI (súbor ai.py)
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