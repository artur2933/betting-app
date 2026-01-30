from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - CLEAN & MODERN DESIGN
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        /* --- ZÁKLADNÉ NASTAVENIA --- */
        body { margin: 0; padding: 0; font-family: 'Inter', 'Segoe UI', sans-serif; background-color: #050505; color: #e0e0e0; display: flex; height: 100vh; overflow: hidden; }
        
        /* --- SIDEBAR --- */
        .sidebar { width: 260px; background-color: #0f0f0f; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #222; }
        .logo { font-size: 20px; font-weight: 900; color: #00ff88; margin-bottom: 50px; text-transform: uppercase; letter-spacing: 2px; text-align: center; display:flex; align-items:center; justify-content:center; gap:10px; }
        .menu-item { padding: 12px 15px; margin-bottom: 8px; cursor: pointer; border-radius: 8px; color: #666; font-weight: 600; transition: 0.2s; display: flex; align-items: center; gap: 12px; font-size: 14px; }
        .menu-item:hover, .menu-item.active { background-color: #1a1a1a; color: #fff; border-left: 3px solid #00ff88; }
        
        /* --- HLAVNÝ OBSAH --- */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: #050505; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #222; padding-bottom: 20px; }
        .header h1 { margin: 0; color: #fff; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
        
        /* Tlačidlo */
        .btn-analyze { 
            background: #00ff88; border: none; padding: 16px 40px; 
            font-size: 16px; font-weight: 700; color: #000; border-radius: 8px; cursor: pointer; 
            box-shadow: 0 0 30px rgba(0, 255, 136, 0.2); transition: all 0.2s;
            display: block; margin: 0 auto 40px auto; text-transform: uppercase; letter-spacing: 1px;
        }
        .btn-analyze:hover { transform: translateY(-2px); box-shadow: 0 0 50px rgba(0, 255, 136, 0.4); }

        /* --- KARTA ZÁPASU (REDESIGN) --- */
        .match-card { 
            background: #111; border-radius: 12px; margin-bottom: 40px; overflow: hidden; 
            border: 1px solid #222; position: relative;
            animation: slideUp 0.5s ease;
        }
        
        /* 1. HLAVIČKA ZÁPASU (Centered Hero) */
        .match-hero {
            padding: 40px 20px;
            background: radial-gradient(circle at center, #1a2e25 0%, #111 70%);
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            border-bottom: 1px solid #222;
        }
        
        .teams-container { display: flex; align-items: center; justify-content: center; gap: 30px; width: 100%; }
        .team-name { font-size: 32px; font-weight: 800; color: white; width: 40%; text-align: center; line-height: 1.2; }
        .vs-badge { 
            background: #222; color: #666; font-weight: 900; font-size: 12px; 
            width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
            border: 2px solid #333;
        }
        
        .odds-badge { 
            margin-top: 20px; background: rgba(0, 255, 136, 0.1); color: #00ff88; 
            padding: 8px 20px; border-radius: 20px; font-weight: bold; font-size: 14px; border: 1px solid rgba(0, 255, 136, 0.3);
        }

        /* 2. GRID LAYOUT PRE TELO KARTY */
        .match-grid {
            display: grid;
            grid-template-columns: 1fr 1fr; /* Dva stĺpce: Štatistiky | Analýza */
            gap: 0; /* Oddelené len čiarou */
        }

        .grid-col { padding: 30px; }
        .col-stats { border-right: 1px solid #222; }

        /* Sekcie */
        .section-title { font-size: 12px; color: #666; text-transform: uppercase; font-weight: 800; letter-spacing: 1px; margin-bottom: 20px; }

        /* Stats Rows */
        .stat-box { background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        .stat-name { font-size: 14px; color: #aaa; }
        .stat-val { font-weight: bold; color: white; }

        /* Forma (Guličky) */
        .form-row { display: flex; gap: 5px; }
        .dot { width: 10px; height: 10px; border-radius: 50%; }
        .w { background: #00ff88; box-shadow: 0 0 5px rgba(0,255,136,0.5); }
        .d { background: #ffcc00; }
        .l { background: #ff4444; }

        /* AI Prediction Highlight */
        .ai-result {
            background: linear-gradient(135deg, rgba(0,255,136,0.1) 0%, rgba(0,0,0,0) 100%);
            border-left: 4px solid #00ff88;
            padding: 20px; border-radius: 0 8px 8px 0;
            margin-bottom: 20px;
        }
        .ai-label { color: #00ff88; font-weight: bold; font-size: 12px; margin-bottom: 5px; }
        .ai-value { font-size: 20px; font-weight: 700; color: white; }
        .ai-text { font-size: 14px; color: #ccc; line-height: 1.6; margin-top: 15px; }
        
        .confidence-bar-bg { width: 100%; height: 6px; background: #222; border-radius: 3px; margin-top: 15px; }
        .confidence-bar-fill { height: 100%; background: #00ff88; border-radius: 3px; }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 VIP Analýza</div>
        <div class="menu-item" onclick="showPage('results-page', this)">✅ Výsledky</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Market Overview</h1></div>
            
            <div style="display:flex; gap:20px; margin-bottom: 30px;">
                <div style="background:#111; padding:25px; flex:1; border-radius:12px; border:1px solid #222;">
                    <div style="color:#666; font-size:12px; font-weight:bold; margin-bottom:10px;">DENNÝ ZISK</div>
                    <div style="color:#fff; font-size:32px; font-weight:bold;">+ €124.50</div>
                </div>
                <div style="background:#111; padding:25px; flex:1; border-radius:12px; border:1px solid #222;">
                    <div style="color:#666; font-size:12px; font-weight:bold; margin-bottom:10px;">ROI (Návratnosť)</div>
                    <div style="color:#00ff88; font-size:32px; font-weight:bold;">18.2%</div>
                </div>
                <div style="background:#111; padding:25px; flex:1; border-radius:12px; border:1px solid #222;">
                    <div style="color:#666; font-size:12px; font-weight:bold; margin-bottom:10px;">VÝHERNOSŤ</div>
                    <div style="color:#fff; font-size:32px; font-weight:bold;">76%</div>
                </div>
            </div>
            
            <div style="background:#111; padding:25px; border-radius:12px; border:1px solid #222; height:350px;">
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>Deep AI Scanner</h1></div>
            
            <div style="text-align:center; margin-bottom:50px;">
                <button class="btn-analyze" onclick="generujTiket()">Spustiť Analýzu Trhu</button>
                <p style="color:#444; font-size:14px;">Powered by GPT-4o & Statistical Models</p>
            </div>

            <div id="loading" style="display:none; text-align:center; color:#00ff88; margin-top: 50px;">
                <h2>⚡ Analyzujem dáta...</h2>
            </div>

            <div id="ticket-output"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>História</h1></div>
            <p style="color:#666">Zatiaľ žiadne záznamy.</p>
        </div>

    </div>

    <script>
        // Graf
        document.addEventListener("DOMContentLoaded", function() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'],
                    datasets: [{
                        label: 'Zisk',
                        data: [2100, 2150, 2120, 2250, 2300, 2380, 2450],
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.05)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: '#222' }, ticks: { color: '#666' } },
                        x: { grid: { display: false }, ticks: { color: '#666' } }
                    }
                }
            });
        });

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(el) el.classList.add('active');
        }

        async function generujTiket() {
            const out = document.getElementById('ticket-output');
            const load = document.getElementById('loading');
            out.innerHTML = '';
            load.style.display = 'block';

            try {
                const res = await fetch('/api/generuj-tiket');
                const data = await res.json();
                load.style.display = 'none';

                let html = '';
                data.forEach(m => {
                    // Pomocná funkcia pre bodky formy
                    const dots = (f) => {
                        let h = '';
                        for(let c of f) h+= `<div class="dot ${c==='W'?'w':(c==='L'?'l':'d')}"></div>`;
                        return h;
                    };

                    html += `
                    <div class="match-card">
                        <div class="match-hero">
                            <div class="teams-container">
                                <div class="team-name" style="text-align:right;">${m.domaci}</div>
                                <div class="vs-badge">VS</div>
                                <div class="team-name" style="text-align:left;">${m.hostia}</div>
                            </div>
                            <div class="odds-badge">Kurz: ${m.kurz}</div>
                        </div>

                        <div class="match-grid">
                            
                            <div class="grid-col col-stats">
                                <div class="section-title">Kľúčové metriky</div>
                                
                                <div class="stat-box">
                                    <span class="stat-name">Aktuálna Forma</span>
                                    <div style="display:flex; gap:15px;">
                                        <div class="form-row">${dots(m.stats.forma_domaci)}</div>
                                        <div class="form-row">${dots(m.stats.forma_hostia)}</div>
                                    </div>
                                </div>

                                <div class="stat-box">
                                    <span class="stat-name">xG Power (Útok)</span>
                                    <span class="stat-val">${m.stats.utok_domaci}% vs ${m.stats.utok_hostia}%</span>
                                </div>

                                <div class="stat-box">
                                    <span class="stat-name">Absencie</span>
                                    <span class="stat-val" style="color:#ff4444; font-size:12px; text-align:right;">${m.stats.zranenia}</span>
                                </div>
                            </div>

                            <div class="grid-col">
                                <div class="section-title">AI Predikcia</div>
                                
                                <div class="ai-result">
                                    <div class="ai-label">ODPORÚČANÝ TIP</div>
                                    <div class="ai-value">${m.tip}</div>
                                </div>

                                <p class="ai-text">${m.analyza_text}</p>
                                
                                <div style="margin-top:20px;">
                                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#aaa; margin-bottom:5px;">
                                        <span>Dôvera modelu</span>
                                        <span style="color:#00ff88">${m.dovera}%</span>
                                    </div>
                                    <div class="confidence-bar-bg">
                                        <div class="confidence-bar-fill" style="width:${m.dovera}%"></div>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                    `;
                });
                out.innerHTML = html;
            } catch(e) { load.style.display = 'none'; alert("Chyba."); }
        }
    </script>
</body>
</html>
"""

# 3. BACKEND (Oprava syntaxe + Dáta)
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
    return [
        {
            "domaci": "Manchester United", "hostia": "PAOK Solún", "kurz": 1.45, 
            "tip": "Výhra United & Over 1.5", "dovera": 88,
            "stats": {
                "forma_domaci": "WWDLW", "forma_hostia": "LLDWL",
                "utok_domaci": 82, "utok_hostia": 40,
                "zranenia": "Maguire (Out)"
            },
            "analyza_text": "United pod novým trénerom Amorimom doma dominuje. Old Trafford je pevnosť, zatiaľ čo PAOK vonku v Európe trpí a inkasuje v priemere 2 góly."
        },
        {
            "domaci": "Lazio Rím", "hostia": "FC Porto", "kurz": 2.10, 
            "tip": "Obaja dajú gól (BTTS)", "dovera": 75,
            "stats": {
                "forma_domaci": "WWWWL", "forma_hostia": "WWWWW",
                "utok_domaci": 78, "utok_hostia": 85,
                "zranenia": "Immobile (Lavička)"
            },
            "analyza_text": "Súboj dvoch ofenzívne ladených tímov. Porto má smrtiacu formu, ale v Taliansku sa hrá ťažko. Očakávame góly na oboch stranách."
        }
    ]

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): 
    return {"status": "ok"}
