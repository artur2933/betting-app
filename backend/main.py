from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# --- GRAFIKA PRE GENERÁTOR TIKETOV ---
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Betting Manager</title>
    <style>
        body { background-color: #050505; color: #fff; font-family: 'Segoe UI', sans-serif; text-align: center; padding: 20px; }
        h1 { color: #00ff88; text-transform: uppercase; letter-spacing: 2px; }
        
        .panel { background: #111; padding: 30px; border-radius: 15px; border: 1px solid #333; max-width: 500px; margin: 0 auto; box-shadow: 0 0 30px rgba(0,255,136,0.1); }
        
        button { 
            width: 100%; padding: 20px; margin-top: 20px; 
            background: linear-gradient(90deg, #00ff88, #00cc6a); 
            border: none; border-radius: 8px; 
            font-size: 20px; font-weight: bold; color: #000; cursor: pointer; 
            transition: transform 0.2s;
        }
        button:hover { transform: scale(1.02); box-shadow: 0 0 15px #00ff88; }
        
        .tiket-box { margin-top: 30px; text-align: left; }
        .zapas-row { background: #222; padding: 15px; margin-bottom: 10px; border-left: 4px solid #00ff88; border-radius: 4px; }
        .kurz { float: right; font-weight: bold; color: #00ff88; }
        .total { font-size: 22px; border-top: 1px solid #444; padding-top: 15px; margin-top: 15px; text-align: right; color: yellow; }
        
        .filters { display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; }
        select { background: #222; color: white; border: 1px solid #444; padding: 10px; border-radius: 5px; width: 100%; }
    </style>
</head>
<body>
    <h1>🎰 AI Ticket Master</h1>
    
    <div class="panel">
        <div class="filters">
            <select id="liga">
                <option value="all">Všetky ligy</option>
                <option value="premier">Premier League</option>
                <option value="laliga">La Liga</option>
            </select>
        </div>

        <p>Nechaj AI, aby našla najlepšiu kombináciu na dnes.</p>
        <button onclick="generujTiket()">⚡ VYTVORIŤ TIKET ⚡</button>

        <div id="vysledok" class="tiket-box" style="display:none;">
            </div>
    </div>

    <script>
        async function generujTiket() {
            const vysledokDiv = document.getElementById('vysledok');
            vysledokDiv.style.display = 'block';
            vysledokDiv.innerHTML = '<p style="text-align:center;">🤖 AI skenuje zápasy a hľadá tutovky...</p>';
            
            try {
                // Zavoláme backend, aby prešiel všetky zápasy
                const res = await fetch('/api/generuj-tiket');
                const data = await res.json();
                
                if (data.length === 0) {
                    vysledokDiv.innerHTML = '<p style="text-align:center; color:red;">Žiadne vhodné zápasy na tiket.</p>';
                    return;
                }

                let html = '<h3>🔥 Dnešný AI Výber:</h3>';
                let celkovyKurz = 1;

                data.forEach(zapas => {
                    celkovyKurz *= zapas.kurz;
                    html += `
                        <div class="zapas-row">
                            <div>${zapas.domaci} vs ${zapas.hostia}</div>
                            <small>${zapas.dovod}</small>
                            <span class="kurz">${zapas.kurz}</span>
                        </div>
                    `;
                });

                html += `<div class="total">Celkový kurz: <b>${celkovyKurz.toFixed(2)}</b></div>`;
                vysledokDiv.innerHTML = html;

            } catch (e) {
                vysledokDiv.innerHTML = '<p style="color:red">Chyba spojenia.</p>';
            }
        }
    </script>
</body>
</html>
"""

def get_db():
    db = database.SessionLocal(); try: yield db; finally: db.close()

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

# --- NOVÁ LOGIKA: GENERÁTOR TIKETU ---
@app.get("/api/generuj-tiket")
def generuj_denny_tiket(db: Session = Depends(get_db)):
    # 1. Načítame VŠETKY zápasy z databázy
    vsetky_zapasy = crud.get_vsetky_zapasy(db)
    
    top_vyber = []
    
    # 2. Prejdeme každý zápas a spýtame sa AI
    for z in vsetky_zapasy:
        # Jednoduchá AI logika (v budúcnosti tu bude napojená real AI)
        # Ak je šanca na výhru domacich vysoká a kurz je zaujímavý
        score = (z.sanca * z.kurz) 
        
        # Ak je to "dobrý deal", pridáme to na tiket
        if score > 1.8: # Filter kvality
            top_vyber.append({
                "domaci": z.domaci,
                "hostia": z.hostia,
                "kurz": z.kurz,
                "tip": "1",
                "dovod": ai.analyzuj_zapas_cez_ai(z.domaci, z.hostia, z.kurz, z.sanca)
            })
    
    # 3. Vyberieme max 3 najlepšie zápasy na tiket
    # (Zoraďujeme podľa kurzu, nech to nie sú len 1.01 kurzy)
    top_vyber = sorted(top_vyber, key=lambda x: x['kurz'], reverse=True)[:3]
    
    return top_vyber

# Pre zachovanie funkčnosti Whopu
class WhopInput(BaseModel): message: str
@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
