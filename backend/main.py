from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - PREMIUM GOLD & NAVY EDITION
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
            --bg-body: #0f172a;       /* Tmavá Navy */
            --bg-card: #1e293b;       /* Svetlejšia Navy */
            --accent: #fbbf24;        /* Zlatá / Amber */
            --accent-glow: rgba(251, 191, 36, 0.3);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #22c55e;
            --danger: #ef4444;
        }

        body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
        
        /* SIDEBAR */
        .sidebar { width: 250px; background-color: #020617; border-right: 1px solid #334155; display: flex; flex-direction: column; padding: 30px 20px; }
        .logo { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 50px; display:flex; align-items:center; gap:10px; }
        .logo span { color: var(--accent); }
        
        .menu-item { padding: 14px; margin-bottom: 8px; cursor: pointer; border-radius: 8px; color: var(--text-muted); font-weight: 600; transition: 0.2s; font-size: 15px; }
        .menu-item:hover, .menu-item.active { background: var(--accent); color: #000; }
        
        /* MAIN CONTENT */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: var(--bg-body); }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .header h1 { margin: 0; font-size: 28px; font-weight: 800; color: #fff; }

        /* TLAČIDLO - Veľké a Výrazné */
        .btn-analyze { 
            background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
            border: none; padding: 20px 80px; width: 100%; max-width: 400px;
            font-size: 18px; font-weight: 800; color: #fff; border-radius: 12px;
            cursor: pointer; transition: all 0.3s; display: block; margin: 0 auto 50px auto; 
            box-shadow: 0 10px 30px rgba(251, 191, 36, 0.2);
            text-transform: uppercase; letter-spacing: 1px;
        }
        .btn-analyze:hover { transform: translateY(-3px); box-shadow: 0 20px 40px rgba(251, 191, 36, 0.4); }

        /* KARTA ZÁPASU - Nový Layout */
        .match-card { 
            background: var(--bg-card); border-radius: 16px; margin-bottom: 30px; 
            border: 1px solid #334155; overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            animation: slideUp 0.5s ease;
        }

        /* HEADER ZÁPASU */
        .card-header {
            padding: 25px; background: rgba(0,0,0,0.2); border-bottom: 1px solid #334155;
            display: flex; justify-content: space-between; align-items: center;
        }
        .league-badge { background: #334155; color: #fff; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; }
        .date-badge { color: var(--text-muted); font-size: 14px; }

        /* TÍMY A SKÓRE */
        .match-teams {
            padding: 40px 20px; display: flex; justify-content: center; align-items: center; gap: 40px;
        }
        .team { text-align: center; width: 35%; }
        .team-name { font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 10px; display: block; }
        .team-odds { background: #0f172a; padding: 6px 15px; border-radius: 8px; color: var(--accent); font-weight: bold; border: 1px solid #334155; }
        
        .vs { 
            width: 50px; height: 50px; background: var(--accent); color: #000; border-radius: 50%; 
            display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 14px;
        }

        /* GRID PRE DATA */
        .data-grid { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid #334155; }
        
        /* ĽAVÁ STRANA - STATS */
        .col-stats { padding: 30px; border-right: 1px solid #334155; }
        
        /* Kruhové Grafy Kontajner */
        .circles-container { display: flex; justify-content: space-around; margin-bottom: 30px; }
        .circle-wrap { text-align: center; }
        .circle-label { font-size: 12px; color: var(--text-muted); margin-top: 10px; font-weight: bold; text-transform: uppercase; }

        /* Custom Kruhový Graf (CSS only) */
        .pie {
            width: 80px; height: 80px; border-radius: 50%; background: conic-gradient(var(--accent) var(--p), #334155 0);
            display: flex; align-items: center; justify-content: center; margin: 0 auto;
        }
        .pie span { 
            width: 65px; height: 65px; background: var(--bg-card); border-radius: 50%; 
            display: flex; align-items: center; justify-content: center; font-weight: bold; color: #fff;
        }

        /* Forma */
        .form-row { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; background: #0f172a; padding: 15px; border-radius: 8px; }
        .dots { display: flex; gap: 5px; }
        .dot { width: 10px; height: 10px; border-radius: 2px; }
        .w { background: var(--success); }
        .d { background: #fbbf24; }
        .l { background: var(--danger); }

        /* PRAVÁ STRANA - AI */
        .col-ai { padding: 30px; background: linear-gradient(180deg, rgba(251, 191, 36, 0.05) 0%, rgba(0,0,0,0) 100%); }
        
        .ai-title { color: var(--accent); font-weight: bold; font-size: 12px; letter-spacing: 1px; margin-bottom: 10px; text-transform: uppercase; }
        .ai-main-tip { font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 15px; }
        .ai-text { font-size: 15px; line-height: 1.6; color: #cbd5e1; }
        
        .confidence-badge { 
            margin-top: 20px; display: inline-flex; align-items: center; gap: 10px; 
            background: rgba(251, 191, 36, 0.1); padding: 8px 16px; border-radius: 20px; border: 1px solid var(--accent-glow);
        }
        .conf-val { color: var(--accent); font-weight: 800; font-size: 18px; }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

        /* Chart Box */
        .chart-container { background: var(--bg-card); padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 30px; height: 300px; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">BET<span>PRO</span></div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Prehľad</div>
        <div class="menu-item" onclick="showPage('generator', this)">🚀 AI Scanner</div>
        <div class="menu-item" onclick="showPage('results-page', this)">📊 Výsledky</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Vitaj späť, Hráč</h1></div>
            
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom: 30px;">
                <div style="background:var(--bg-card); padding:25px; border-radius:12px; border:1px solid #334155;">
                    <div style="color:var(--text-muted); font-size:12px; font-weight:bold; margin-bottom:5px;">BANKROLL</div>
                    <div style="color:#fff; font-size:36px; font-weight:800;">€2,450.00</div>
                    <div style="color:var(--success); font-size:14px; font-weight:bold;">▲ +12.5%</div>
                </div>
                <div style="background:var(--bg-card); padding:25px; border-radius:12px; border:1px solid #334155;">
                    <div style="color:var(--text-muted); font-size:12px; font-weight:bold; margin-bottom:5px;">AI ÚSPEŠNOSŤ (7 DNÍ)</div>
                    <div style="color:var(--accent); font-size:36px; font-weight:800;">78.4%</div>
                    <div style="color:var(--text-muted); font-size:14px;">21 výhier / 6 prehier</div>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>AI Market Scanner</h1></div>
            
            <div style="text-align:center;">
                <button class="btn-analyze" onclick="generujTiket()">Skenovať Zápasy</button>
            </div>

            <div id="loading" style="display:none; text-align:center; color:var(--accent); margin-top: 50px;">
                <h2>⏳ Analyzujem trh a kurzy...</h2>
            </div>

            <div id="ticket-output"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>História</h1></div>
            <p style="color:#666">História je zatiaľ prázdna.</p>
        </div>

    </div>

    <script>
        // Graf Zisku
        document.addEventListener("DOMContentLoaded", function() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'],
                    datasets: [{
                        label: 'Zisk (€)',
                        data: [2100, 2150, 2120, 2250, 2300, 2380, 2450],
                        borderColor: '#fbbf24',
                        backgroundColor: 'rgba(251, 191, 36, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 4,
                        pointBackgroundColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
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
                    const dots = (f) => {
                        let h = '';
                        for(let c of f) h+= `<div class="dot ${c==='W'?'w':(c==='L'?'l':'d')}"></div>`;
                        return h;
                    };

                    html += `
                    <div class="match-card">
                        <div class="card-header">
                            <div class="league-badge">UEFA Europa League</div>
                            <div class="date-badge">Dnes, 21:00</div>
                        </div>

                        <div class="match-teams">
                            <div class="team">
                                <span class="team-name">${m.domaci}</span>
                                <span class="team-odds">${(1 + Math.random()).toFixed(2)}</span>
                            </div>
                            <div class="vs">VS</div>
                            <div class="team">
                                <span class="team-name">${m.hostia}</span>
                                <span class="team-odds">${(2 + Math.random()).toFixed(2)}</span>
                            </div>
                        </div>

                        <div class="data-grid">
                            <div class="col-stats">
                                <div class="circles-container">
                                    <div class="circle-wrap">
                                        <div class="pie" style="--p:${m.stats.utok_domaci}%"><span>${m.stats.utok_domaci}</span></div>
                                        <div class="circle-label">Útok Home</div>
                                    </div>
                                    <div class="circle-wrap">
                                        <div class="pie" style="--p:${m.stats.utok_hostia}%"><span>${m.stats.utok_hostia}</span></div>
                                        <div class="circle-label">Útok Away</div>
                                    </div>
                                </div>
                                
                                <div class="form-row">
                                    <div style="color:#aaa; font-size:12px;">FORMA</div>
                                    <div class="dots">${dots(m.stats.forma_domaci)}</div>
                                    <div style="color:#555;">vs</div>
                                    <div class="dots">${dots(m.stats.forma_hostia)}</div>
                                </div>
                                <div style="margin-top:15px; font-size:13px; color:#ef4444; text-align:center;">
                                    ⚠️ ${m.stats.zranenia}
                                </div>
                            </div>

                            <div class="col-ai">
                                <div class="ai-title">AI ODPORÚČANIE</div>
                                <div class="ai-main-tip">${m.tip}</div>
                                <p class="ai-text">${m.analyza_text}</p>
                                
                                <div class="confidence-badge">
                                    <span style="font-size:12px; color:#aaa;">DÔVERA:</span>
                                    <span class="conf-val">${m.dovera}%</span>
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
            "domaci": "Man Utd", "hostia": "PAOK", "kurz": 1.45, 
            "tip": "United + Over 1.5", "dovera": 88,
            "stats": {
                "forma_domaci": "WWDLW", "forma_hostia": "LLDWL",
                "utok_domaci": 85, "utok_hostia": 45,
                "zranenia": "Maguire (Out)"
            },
            "analyza_text": "United pod novým trénerom Amorimom doma dominuje. Old Trafford je pevnosť, zatiaľ čo PAOK vonku v Európe trpí a inkasuje v priemere 2 góly."
        },
        {
            "domaci": "Lazio", "hostia": "Porto", "kurz": 2.10, 
            "tip": "BTTS (Obaja gól)", "dovera": 75,
            "stats": {
                "forma_domaci": "WWWWL", "forma_hostia": "WWWWW",
                "utok_domaci": 78, "utok_hostia": 82,
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
