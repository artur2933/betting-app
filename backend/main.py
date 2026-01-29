from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# --- PROFESIONÁLNY DASHBOARD UI ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <title>Betting PRO Dashboard</title>
    <style>
        /* Základný štýl pre celú aplikáciu */
        body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background-color: #0d0d0d; color: white; display: flex; height: 100vh; overflow: hidden; }
        
        /* Bočné menu (Sidebar) */
        .sidebar { width: 250px; background-color: #161616; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 20px; }
        .logo { font-size: 24px; font-weight: bold; color: #00ff88; margin-bottom: 40px; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
        
        .menu-item { padding: 15px; margin-bottom: 10px; cursor: pointer; border-radius: 8px; color: #aaa; transition: 0.3s; font-size: 16px; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background-color: #00ff88; color: black; font-weight: bold; }
        
        /* Hlavná časť (Content) */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1a1a1a 0%, #0d0d0d 60%); }
        
        /* Karty a sekcie */
        .page { display: none; animation: fadeIn 0.3s; }
        .page.active { display: block; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .header h2 { margin: 0; font-size: 28px; }
        
        .card { background: #1a1a1a; padding: 25px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .card h3 { margin-top: 0; color: #00ff88; }
        
        /* Tlačidlá */
        .btn { background: #00ff88; color: black; padding: 12px 25px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #00cc6a; }

        /* Tabuľka tiketov */
        .ticket-row { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #333; }
        .ticket-row:last-child { border-bottom: none; }
        .odds { font-weight: bold; color: #00ff88; }
        
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BetBot AI</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Prehľad</div>
        <div class="menu-item" onclick="showPage('generator', this)">⚽ VIP Generátor</div>
        <div class="menu-item" onclick="showPage('history', this)">📊 História</div>
        <div class="menu-item" onclick="showPage('settings', this)">⚙️ Nastavenia</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header">
                <h2>Vitaj späť, Hráč</h2>
                <span style="color: #666;">Verzia 1.0</span>
            </div>
            
            <div style="display: flex; gap: 20px;">
                <div class="card" style="flex: 1;">
                    <h3>💰 Tvoj Bankroll</h3>
                    <p style="font-size: 32px; font-weight: bold; margin: 10px 0;">€0.00</p>
                    <small style="color: #888;">Zatiaľ len simulácia</small>
                </div>
                <div class="card" style="flex: 1;">
                    <h3>📈 Úspešnosť AI</h3>
                    <p style="font-size: 32px; font-weight: bold; margin: 10px 0;">87%</p>
                    <small style="color: #888;">Posledných 30 dní</small>
                </div>
            </div>

            <div class="card">
                <h3>📢 Novinky</h3>
                <p>AI model bol aktualizovaný na verziu 2.0. Pridaná podpora pre Premier League.</p>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h2>Generátor Denného Tiketu</h2></div>
            <div class="card">
                <p>Klikni na tlačidlo a nechaj umelú inteligenciu analyzovať tisíce dát.</p>
                <button class="btn" onclick="generujTiket()">⚡ Analyzovať a Vytvoriť Tiket</button>
            </div>
            <div id="ticket-result" class="card" style="display:none; border: 1px solid #00ff88;">
                </div>
        </div>

        <div id="history" class="page">
            <div class="header"><h2>História Tiketov</h2></div>
            <div class="card">
                <div class="ticket-row">
                    <span>Arsenal vs Chelsea</span>
                    <span style="color: #00ff88;">VÝHRA ✅</span>
                </div>
                <div class="ticket-row">
                    <span>Real Madrid vs Barcelona</span>
                    <span style="color: red;">PREHRA ❌</span>
                </div>
                <div class="ticket-row">
                    <span>Bayern vs Dortmund</span>
                    <span style="color: #00ff88;">VÝHRA ✅</span>
                </div>
            </div>
        </div>
        
         <div id="settings" class="page">
            <div class="header"><h2>Nastavenia</h2></div>
            <div class="card">
                <p>Tu si budeš môcť nastaviť notifikácie a obľúbené ligy.</p>
            </div>
        </div>

    </div>

    <script>
        // Prepínanie stránok v menu
        function showPage(pageId, element) {
            // Skryť všetky stránky
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            
            // Zobraziť vybranú
            document.getElementById(pageId).classList.add('active');
            element.classList.add('active');
        }

        // Funkcia na generovanie tiketu (napojená na Python backend)
        async function generujTiket() {
            const div = document.getElementById('ticket-result');
            div.style.display = 'block';
            div.innerHTML = '<p>⏳ AI analyzuje zápasy...</p>';
            
            try {
                const res = await fetch('/api/generuj-tiket');
                const data = await res.json();
                
                if (data.length === 0) {
                    div.innerHTML = '<p>Žiadne vhodné zápasy.</p>';
                    return;
                }

                let html = '<h3>🔥 Dnešný AI Výber:</h3>';
                let totalOdds = 1;
                
                data.forEach(z => {
                    totalOdds *= z.kurz;
                    html += `<div class="ticket-row">
                                <div><b>${z.domaci} vs ${z.hostia}</b><br><small style="color:#aaa">${z.dovod}</small></div>
                                <div class="odds">${z.kurz}</div>
                             </div>`;
                });
                
                html += `<div style="margin-top:20px; text-align:right; font-size:20px;">Celkový kurz: <b style="color:#00ff88">${totalOdds.toFixed(2)}</b></div>`;
                div.innerHTML = html;
            } catch(e) {
                div.innerHTML = '<p style="color:red">Chyba spojenia so serverom.</p>';
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

@app.get("/api/generuj-tiket")
def generuj_denny_tiket(db: Session = Depends(get_db)):
    vsetky = crud.get_vsetky_zapasy(db)
    top = []
    for z in vsetky:
        score = (z.sanca * z.kurz) 
        if score > 1.8:
            top.append({
                "domaci": z.domaci,
                "hostia": z.hostia,
                "kurz": z.kurz,
                "dovod": ai.analyzuj_zapas_cez_ai(z.domaci, z.hostia, z.kurz, z.sanca)
            })
    return sorted(top, key=lambda x: x['kurz'], reverse=True)[:3]

class WhopInput(BaseModel): message: str
@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
