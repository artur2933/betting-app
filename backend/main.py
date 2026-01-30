from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - PREMIUM GOLD & NAVY (S Tiketom Dňa a Vlastným Generátorom)
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    
    <style>
        /* --- PREMIUM THEME --- */
        :root {
            --bg-body: #0f172a;       
            --bg-card: #1e293b;       
            --accent: #fbbf24;        /* Zlatá */
            --accent-glow: rgba(251, 191, 36, 0.3);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #22c55e;
            --danger: #ef4444;
        }

        body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
        
        /* SIDEBAR */
        .sidebar { width: 250px; background-color: #020617; border-right: 1px solid #334155; display: flex; flex-direction: column; padding: 30px 20px; }
        .logo { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 40px; display:flex; align-items:center; gap:10px; }
        .logo span { color: var(--accent); }
        
        .menu-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; margin-top: 20px; }
        
        .menu-item { padding: 14px; margin-bottom: 8px; cursor: pointer; border-radius: 8px; color: var(--text-muted); font-weight: 600; transition: 0.2s; font-size: 15px; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background: var(--accent); color: #000; box-shadow: 0 0 15px var(--accent-glow); }
        
        /* MAIN CONTENT */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: var(--bg-body); }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .header h1 { margin: 0; font-size: 28px; font-weight: 800; color: #fff; }

        /* --- TIKET DŇA (ŠPECIÁLNA KARTA) --- */
        .ticket-of-day-card {
            background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
            border: 2px solid var(--accent);
            border-radius: 16px;
            padding: 0;
            overflow: hidden;
            box-shadow: 0 0 40px rgba(251, 191, 36, 0.15);
            animation: slideUp 0.5s ease;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .tod-header {
            background: var(--accent); color: #000; padding: 15px 30px; 
            font-weight: 800; font-size: 18px; text-transform: uppercase; letter-spacing: 2px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .tod-body { padding: 30px; display: grid; grid-template-columns: 2fr 1fr; gap: 30px; }
        
        .tod-match { margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 15px; }
        .tod-match:last-child { border-bottom: none; }
        .tod-teams { font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 5px; }
        .tod-tip { color: var(--accent); font-weight: bold; font-size: 16px; }
        
        .tod-stats { text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center; border-left: 1px solid #334155; }
        .tod-confidence-circle {
            width: 100px; height: 100px; border-radius: 50%;
            background: conic-gradient(var(--success) 90%, #334155 0);
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 10px;
            box-shadow: 0 0 20px rgba(34, 197, 94, 0.4);
        }
        .tod-conf-val { background: var(--bg-card); width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 800; color: #fff; }
        
        /* --- VLASTNÝ GENERÁTOR (FORMULÁR) --- */
        .custom-gen-box {
            background: var(--bg-card); border-radius: 16px; padding: 40px; border: 1px solid #334155;
            max-width: 700px; margin: 0 auto;
        }
        
        .control-group { margin-bottom: 30px; }
        .control-label { display: block; color: var(--text-muted); margin-bottom: 10px; font-weight: 600; font-size: 14px; text-transform: uppercase; }
        
        /* Range Slider */
        input[type=range] { width: 100%; -webkit-appearance: none; background: transparent; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; height: 20px; width: 20px; border-radius: 50%; background: var(--accent); cursor: pointer; margin-top: -8px; box-shadow: 0 0 10px var(--accent); }
        input[type=range]::-webkit-slider-runnable-track { width: 100%; height: 4px; cursor: pointer; background: #334155; border-radius: 2px; }
        
        .range-values { display: flex; justify-content: space-between; color: #fff; font-weight: bold; margin-top: 10px; }
        
        /* Dropdown */
        select { width: 100%; padding: 15px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 8px; font-size: 16px; outline: none; }
        select:focus { border-color: var(--accent); }

        .btn-generate-custom {
            background: var(--accent); color: #000; width: 100%; padding: 18px; border: none; border-radius: 8px; font-weight: 800; font-size: 18px; cursor: pointer; transition: 0.3s; text-transform: uppercase;
        }
        .btn-generate-custom:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(251, 191, 36, 0.3); }

        /* Pôvodné štýly (pre zachovanie funkcionality) */
        .match-card { background: var(--bg-card); border-radius: 12px; margin-bottom: 20px; border: 1px solid #334155; padding: 20px; animation: slideUp 0.5s ease; }
        .teams-title { font-size: 18px; font-weight: bold; color: #fff; }
        .match-meta { color: var(--accent); font-weight: bold; float: right; }
        
        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">BET<span>PRO</span></div>
        
        <div class="menu-label">Hlavné</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('ticket-day', this)">🎯 Tiket Dňa</div>
        
        <div class="menu-label">Nástroje</div>
        <div class="menu-item" onclick="showPage('custom-gen', this)">🛠️ Vlastný Generátor</div>
        <div class="menu-item" onclick="showPage('scanner', this)">🚀 AI Scanner (Všetko)</div>
        
        <div class="menu-label">Dáta</div>
        <div class="menu-item" onclick="showPage('results-page', this)">📊 Výsledky</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Prehľad</h1></div>
            <div style="background:var(--bg-card); padding:30px; border-radius:12px; border:1px solid #334155; text-align:center;">
                <h2 style="color:white;">Vitaj v systéme 2.0</h2>
                <p style="color:var(--text-muted)">Vyber si z menu vľavo: Tiket dňa alebo si vygeneruj vlastný.</p>
            </div>
        </div>

        <div id="ticket-day" class="page">
            <div class="header"><h1>🔥 TIKET DŇA</h1></div>
            
            <div class="ticket-of-day-card">
                <div class="tod-header">
                    <span>VIP VÝBER</span>
                    <span>31. Január 2026</span>
                </div>
                <div class="tod-body">
                    <div class="tod-matches">
                        <div class="tod-match">
                            <div style="font-size:12px; color:#94a3b8; margin-bottom:5px;">PREMIER LEAGUE</div>
                            <div class="tod-teams">Man Utd vs Arsenal</div>
                            <div class="tod-tip">Tip: Over 2.5 Gólov <span style="color:#fff; background:#334155; padding:2px 8px; border-radius:4px; font-size:12px; margin-left:10px;">1.75</span></div>
                        </div>
                        <div class="tod-match">
                            <div style="font-size:12px; color:#94a3b8; margin-bottom:5px;">SERIE A</div>
                            <div class="tod-teams">Juventus vs AC Milan</div>
                            <div class="tod-tip">Tip: Remíza v polčase <span style="color:#fff; background:#334155; padding:2px 8px; border-radius:4px; font-size:12px; margin-left:10px;">2.10</span></div>
                        </div>
                        <div style="margin-top:20px; font-size:18px;">
                            Celkový kurz: <span style="color:var(--accent); font-weight:800; font-size:24px;">3.67</span>
                        </div>
                    </div>
                    
                    <div class="tod-stats">
                        <div style="color:var(--text-muted); font-size:12px; font-weight:bold; margin-bottom:10px; text-transform:uppercase;">Dôvera Tiketu</div>
                        <div class="tod-confidence-circle">
                            <div class="tod-conf-val">92%</div>
                        </div>
                        <div style="color:var(--success); font-size:14px; font-weight:bold; margin-top:10px;">Vysoká Pravdepodobnosť</div>
                    </div>
                </div>
            </div>
        </div>

        <div id="custom-gen" class="page">
            <div class="header"><h1>⚙️ Nastav si vlastný tiket</h1></div>
            
            <div class="custom-gen-box">
                <div class="control-group">
                    <label class="control-label">Úroveň Rizika (Risk Level)</label>
                    <input type="range" min="1" max="3" value="2" id="riskSlider" oninput="updateRiskText(this.value)">
                    <div class="range-values">
                        <span id="riskText" style="color:var(--accent);">Stredné Riziko</span>
                    </div>
                </div>

                <div class="control-group">
                    <label class="control-label">Preferovaná Liga</label>
                    <select id="leagueSelect">
                        <option value="all">Všetky Ligy (Mix)</option>
                        <option value="pl">Premier League</option>
                        <option value="laliga">La Liga</option>
                        <option value="bundesliga">Bundesliga</option>
                    </select>
                </div>

                <div class="control-group">
                    <label class="control-label">Počet zápasov na tikete</label>
                    <select id="matchCount">
                        <option value="1">SOLO (1 zápas)</option>
                        <option value="2">AKO (2 zápasy)</option>
                        <option value="3">AKO (3 zápasy)</option>
                        <option value="5">Plachta (5+ zápasov)</option>
                    </select>
                </div>

                <button class="btn-generate-custom" onclick="generujVlastnyTiket()">🤖 Vygenerovať Tiket na Mieru</button>
            </div>

            <div id="custom-result" style="margin-top:40px;"></div>
        </div>

        <div id="scanner" class="page">
            <div class="header"><h1>Celkový Prehľad Trhu</h1></div>
            <div style="text-align:center; margin-bottom:20px;">
                <button class="btn-analyze" style="padding:10px 30px; font-size:14px;" onclick="generujScanner()">Načítať Všetky Zápasy</button>
            </div>
            <div id="scanner-output"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>História</h1></div>
            <p style="color:#666">História je prázdna.</p>
        </div>

    </div>

    <script>
        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(el) el.classList.add('active');
        }

        function updateRiskText(val) {
            const text = document.getElementById('riskText');
            if(val == 1) { text.innerText = "Bezpečné (Nízky kurz)"; text.style.color = "#22c55e"; }
            else if(val == 2) { text.innerText = "Stredné Riziko (Value)"; text.style.color = "#fbbf24"; }
            else { text.innerText = "Vysoké Riziko (Veľký kurz)"; text.style.color = "#ef4444"; }
        }

        // MOCK FUNKCIA PRE VLASTNÝ GENERÁTOR
        async function generujVlastnyTiket() {
            const div = document.getElementById('custom-result');
            div.innerHTML = '<div style="text-align:center; color:var(--accent);"><h3>⏳ AI hľadá zápasy podľa tvojich nastavení...</h3></div>';
            
            // Simulácia čakania
            await new Promise(r => setTimeout(r, 1500));

            const risk = document.getElementById('riskSlider').value;
            let tipType = risk == 1 ? "Dvojitá šanca 1X" : (risk == 2 ? "Výhra domácich" : "Presný výsledok 2:1");
            let odds = risk == 1 ? "1.35" : (risk == 2 ? "2.10" : "8.50");

            div.innerHTML = `
                <div class="match-card" style="border-color:var(--accent);">
                    <div style="display:flex; justify-content:space-between;">
                        <div class="teams-title">Barcelona vs Real Madrid</div>
                        <div class="match-meta">Kurz: ${odds}</div>
                    </div>
                    <div style="margin-top:10px; color:#ccc;">
                        AI vybrala tento zápas na základe tvojho nastavenia rizika.<br>
                        <b>Tip: ${tipType}</b>
                    </div>
                </div>
            `;
        }

        // Pôvodný Scanner
        async function generujScanner() {
            const out = document.getElementById('scanner-output');
            out.innerHTML = 'Načítavam...';
            try {
                const res = await fetch('/api/generuj-tiket');
                const data = await res.json();
                let html = '';
                data.forEach(m => {
                    html += `<div class="match-card"><div class="teams-title">${m.domaci} vs ${m.hostia}</div><div class="match-meta">${m.kurz}</div><br><small style="color:#aaa">${m.analyza_text}</small></div>`;
                });
                out.innerHTML = html;
            } catch(e) { out.innerHTML = 'Chyba'; }
        }
    </script>
</body>
</html>
"""

# 3. BACKEND 
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
    # Dáta pre Scanner (Všeobecné)
    return [
        {
            "domaci": "Man Utd", "hostia": "PAOK", "kurz": 1.45, 
            "tip": "Výhra United", "dovera": 88,
            "stats": {"zranenia": "Maguire (Out)"},
            "analyza_text": "United doma dominuje."
        },
        {
            "domaci": "Lazio", "hostia": "Porto", "kurz": 2.10, 
            "tip": "BTTS", "dovera": 75,
            "stats": {"zranenia": "Immobile"},
            "analyza_text": "Očakávame góly."
        }
    ]

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): 
    return {"status": "ok"}
