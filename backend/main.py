from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel

# Vytvorenie databázy
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# --- TOTO JE TVOJA NOVÁ GRAFIKA (HTML) ---
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Betting AI Bot</title>
    <style>
        body { background-color: #1a1a1a; color: white; font-family: sans-serif; text-align: center; padding: 50px; }
        h1 { color: #00ff88; }
        input { padding: 15px; border-radius: 5px; border: none; width: 200px; text-align: center; }
        button { padding: 15px 30px; background-color: #00ff88; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; }
        button:hover { background-color: #00cc6a; }
        #vysledok { margin-top: 30px; padding: 20px; border: 1px solid #333; display: none; background-color: #252525; border-radius: 10px;}
    </style>
</head>
<body>
    <h1>🤖 AI Betting Analytik</h1>
    <p>Zadaj ID zápasu a nechaj AI rozhodnúť.</p>
    
    <input type="number" id="zapasId" placeholder="ID Zápasu (napr. 1)">
    <button onclick="analyzuj()">Analyzovať</button>

    <div id="vysledok">
        <h3 id="zapasNazov"></h3>
        <p id="aiNazor" style="font-size: 1.2em;"></p>
    </div>

    <script>
        async function analyzuj() {
            const id = document.getElementById('zapasId').value;
            const vysledokDiv = document.getElementById('vysledok');
            
            if(!id) { alert("Zadaj ID!"); return; }

            vysledokDiv.style.display = "block";
            document.getElementById('zapasNazov').innerText = "Načítavam...";
            document.getElementById('aiNazor').innerText = "⏳ AI premýšľa...";

            try {
                const response = await fetch(`/analyzuj/${id}`);
                const data = await response.json();
                
                if (data.chyba) {
                    document.getElementById('zapasNazov').innerText = "Chyba";
                    document.getElementById('aiNazor').innerText = data.chyba;
                } else {
                    document.getElementById('zapasNazov').innerText = data.zapas;
                    document.getElementById('aiNazor').innerText = data.AI_Analytik_Hovori;
                }
            } catch (error) {
                document.getElementById('aiNazor').innerText = "Chyba pripojenia.";
            }
        }
    </script>
</body>
</html>
"""

# Pomocná funkcia pre databázu
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- TOTO ZOBRAZÍ GRAFIKU NA HLAVNEJ STRÁNKE ---
@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

@app.get("/zapasy")
def citat_zapasy(db: Session = Depends(get_db)):
    return crud.get_vsetky_zapasy(db)

@app.get("/analyzuj/{zapas_id}")
def spytat_sa_ai(zapas_id: int, db: Session = Depends(get_db)):
    zapas = db.query(models.Zapas).filter(models.Zapas.id == zapas_id).first()
    if not zapas:
        return {"chyba": "Zápas s týmto ID neexistuje."}
    
    nazor_ai = ai.analyzuj_zapas_cez_ai(
        domaci=zapas.domaci, hostia=zapas.hostia,
        kurz=zapas.kurz, sanca=zapas.sanca
    )
    return {"zapas": f"{zapas.domaci} vs {zapas.hostia}", "AI_Analytik_Hovori": nazor_ai}

# --- WHOP KOMUNIKÁCIA ---
class WhopInput(BaseModel):
    message: str
    user_id: str | None = None

@app.post("/whop")
def komunikacia_s_whop(data: WhopInput):
    return {"response_message": f"AI Analytik: Prijal som správu '{data.message}'"}