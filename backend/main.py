from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA (DASHBOARD)
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Dashboard</title>
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; background-color: #0d0d0d; color: white; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 260px; background-color: #111; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 25px; }
        .logo { font-size: 24px; font-weight: bold; color: #00ff88; margin-bottom: 50px; }
        .menu-item { padding: 15px; margin-bottom: 8px; cursor: pointer; border-radius: 10px; color: #888; display: flex; gap: 10px; }
        .menu-item:hover, .menu-item.active { background-color: #1a1a1a; color: white; font-weight: bold; border-left: 4px solid #00ff88;}
        .main-content { flex: 1; padding: 40px; overflow-y: auto; }
        .card { background: #1a1a1a; padding: 25px; border-radius: 16px; border: 1px solid #2a2a2a; margin-bottom: 20px; }
        .btn-main { background: #00ff88; color: black; border: none; padding: 15px 40px; font-size: 18px; font-weight: bold; border-radius: 50px; cursor: pointer; width: 100%; margin-top: 20px;}
        .btn-main:hover { background-color: #00cc6a; }
        .ticket-item { background: #222; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #00ff88; display: flex; justify-content: space-between;}
        .page { display: none; }
        .page.active { display: block; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">⚡ BETTING AI</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">⚽ VIP Generátor</div>
        <div class="menu-item" onclick="showPage('history', this)">📜 História</div>
    </div>

    <div class="main-content">
        <div id="home" class="page active">
            <h1>Vitaj späť</h1>
            <div class="card">
                <h3>💰 Bankroll: €2,450.00</h3>
                <h3>📈 Úspešnosť AI: 78%</h3>
            </div>
        </div>

        <div id="generator" class="page">
            <h1>AI Generátor Tiketov</h1>
            <div class="card" style="text-align: center;">
                <p>Klikni a nechaj AI nájsť najlepšie dnešné zápasy.</p>
                <button class="btn-main" onclick="generujTiket()">🚀 VYTVORIŤ TIKET</button>
            </div>
            <div id="loading" style="display:none; text-align:center; color:#00ff88; margin-top:20px;">⏳ Analyzujem...</div>
            <div id="ticket-output" style="margin-top: 30px;"></div>
        </div>

        <div id="history" class="page">
            <h1>História</h1>
            <div class="card">
                <div class="ticket-item"><div>Arsenal vs Chelsea</div><div>VÝHRA ✅</div></div>
            </div>
        </div>
    </div>

    <script>
        function showPage(pageId, element) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.getElementById(pageId).classList.add('active');
            element.classList.add('active');
        }

        async function generujTiket() {
            document.getElementById('ticket-output').innerHTML = '';
            document.getElementById('loading').style.display = 'block';
            try {
                const res = await fetch('/api/generuj-tiket');
                const data = await res.json();
                document.getElementById('loading').style.display = 'none';
                
                let html = '<h3>🔥 Dnešný výber:</h3>';
                data.forEach(m => {
                    html += `<div class="ticket-item"><div><b>${m.domaci} vs ${m.hostia}</b><br><small>${m.dovod}</small></div><div>${m.kurz}</div></div>`;
                });
                document.getElementById('ticket-output').innerHTML = html;
            } catch (e) { alert("Chyba spojenia"); }
        }
    </script>
</body>
</html>
"""

# 3. BACKEND (Opravená chyba SyntaxError)
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

@app.get("/api/generuj-tiket")
def generuj_denny_tiket(db: Session = Depends(get_db)):
    vsetky = crud.get_vsetky_zapasy(db)
    
    # Záložné dáta, ak je databáza prázdna (aby si hneď niečo videl)
    if not vsetky:
        data = [
            {"domaci": "Ajax", "hostia": "Besiktas", "kurz": 1.95, "sanca": 70},
            {"domaci": "AS Roma", "hostia": "Bilbao", "kurz": 2.10, "sanca": 65},
            {"domaci": "Tottenham", "hostia": "Qarabag", "kurz": 1.30, "sanca": 85}
        ]
    else:
        data = [{"domaci": z.domaci, "hostia": z.hostia, "kurz": z.kurz, "sanca": z.sanca} for z in vsetky]

    # AI Analýza
    tiket = []
    for z in data:
        score = z['sanca'] * z['kurz']
        tiket.append({
            "domaci": z['domaci'], "hostia": z['hostia'], "kurz": z['kurz'],
            "dovod": ai.analyzuj_zapas_cez_ai(z['domaci'], z['hostia'], z['kurz'], z['sanca'])
        })
    return tiket

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput):
    return {"status": "ok"}