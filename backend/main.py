from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - BLUE CYBERPUNK EDITION
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
    
    <style>
        /* --- CYBERPUNK THEME --- */
        :root {
            --bg-dark: #050a10;
            --bg-card: #0f1621;
            --primary: #00f3ff; /* Elektrická Modrá */
            --secondary: #0088ff;
            --text-main: #e0f7fa;
            --text-muted: #6b8c9e;
            --border: #1e2a3b;
            --danger: #ff0055;
            --success: #00ff9d;
        }

        body { margin: 0; padding: 0; font-family: 'Rajdhani', sans-serif; background-color: var(--bg-dark); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
        
        /* SIDEBAR */
        .sidebar { width: 260px; background-color: #0a0e14; border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 30px 20px; }
        .logo { font-size: 26px; font-weight: 700; color: var(--primary); margin-bottom: 50px; text-transform: uppercase; letter-spacing: 2px; text-align: center; text-shadow: 0 0 15px rgba(0, 243, 255, 0.5); }
        .menu-item { padding: 15px; margin-bottom: 10px; cursor: pointer; border-radius: 6px; color: var(--text-muted); font-weight: 600; transition: 0.3s; display: flex; align-items: center; gap: 15px; font-size: 18px; }
        .menu-item:hover, .menu-item.active { background: rgba(0, 243, 255, 0.1); color: var(--primary); border-right: 3px solid var(--primary); }
        
        /* MAIN CONTENT */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #0f1824 0%, var(--bg-dark) 80%); }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }
        .header h1 { margin: 0; font-size: 32px; font-weight: 700; letter-spacing: 1px; }
        
        /* TLAČIDLO */
        .btn-analyze { 
            background: var(--primary); border: none; padding: 18px 60px; 
            font-size: 18px; font-weight: 800; color: #000; clip-path: polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%);
            cursor: pointer; transition: all 0.3s; display: block; margin: 0 auto 50px auto; text-transform: uppercase; letter-spacing: 2px;
        }
        .btn-analyze:hover { transform: scale(1.05); box-shadow: 0 0 30px rgba(0, 243, 255, 0.6); background: #fff; }

        /* KARTA ZÁPASU */
        .match-card { 
            background: var(--bg-card); border-radius: 4px; margin-bottom: 40px; 
            border: 1px solid var(--border); position: relative; overflow: hidden;
            animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }
        
        .match-card::before {
            content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: var(--primary);
        }

        /* HERO HEADER (VS) */
        .match-header {
            padding: 30px; background: linear-gradient(90deg, rgba(0,243,255,0.05) 0%, transparent 100%);
            display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border);
        }
        
        .team-box { text-align: center; flex: 1; }
        .team-name { font-size: 36px; font-weight: 700; letter-spacing: 1px; color: #fff; margin-bottom: 5px; }
        .team-meta { font-size: 14px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 2px; }
        
        .vs-circle { 
            width: 50px; height: 50px; background: #000; border: 2px solid var(--primary); border-radius: 50%; 
            display: flex; align-items: center; justify-content: center; font-weight: 900; color: var(--primary); font-size: 14px;
            box-shadow: 0 0 20px rgba(0,243,255,0.3);
        }

        /* GRID ŠTATISTÍK */
        .stats-grid {
            display: grid; grid-template-columns: 3fr 2fr; gap: 0;
        }
        .left-panel { padding: 30px; border-right: 1px solid var(--border); }
        .right-panel { padding: 30px; background: rgba(0,0,0,0.2); }

        /* PROGRESS BARY */
        .stat-row { margin-bottom: 25px; }
        .stat-header { display: flex; justify-content: space-between; font-size: 14px; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; font-weight: 700; }
        .bar-container { display: flex; gap: 5px; height: 10px; background: #000; }
        .bar-home { background: var(--primary); height: 100%; transition: width 1s; }
        .bar-away { background: var(--danger); height: 100%; transition: width 1s; }

        /* AI BOX */
        .ai-prediction {
            background: rgba(0, 243, 255, 0.05); border: 1px solid var(--primary); padding: 20px;
            text-align: center; margin-bottom: 20px; position: relative;
        }
        .ai-prediction::after { content: 'AI CONFIRMED'; position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: #000; color: var(--primary); font-size: 10px; padding: 2px 8px; border: 1px solid var(--primary); }
        
        .tip-val { font-size: 24px; font-weight: 700; color: #fff; margin: 10px 0; }
        .confidence { font-size: 40px; font-weight: 900; color: var(--primary); display: block; line-height: 1; text-shadow: 0 0 20px rgba(0,243,255,0.5); }
        .conf-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 2px; }

        /* FORMA DOTS */
        .form-dots { display: flex; gap: 4px; justify-content: center; margin-top: 5px; }
        .dot { width: 8px; height: 8px; border-radius: 2px; }
        .w { background: var(--success); }
        .d { background: #ffcc00; }
        .l { background: var(--danger); }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 AI Scanner</div>
        <div class="menu-item" onclick="showPage('results-page', this)">✅ Výsledky</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>MARKET OVERVIEW</h1></div>
            
            <div style="display:flex; gap:20px; margin-bottom: 30px;">
                <div style="background:var(--bg-card); padding:30px; flex:1; border:1px solid var(--border);">
                    <div style="color:var(--text-muted); font-size:12px; font-weight:bold;">DENNÝ ZISK</div>
                    <div style="color:#fff; font-size:42px; font-weight:bold; margin-top:5px;">+ €124.50</div>
                </div>
                <div style="background:var(--bg-card); padding:30px; flex:1; border:1px solid var(--border);">
                    <div style="color:var(--text-muted); font-size:12px; font-weight:bold;">AI ÚSPEŠNOSŤ</div>
                    <div style="color:var(--primary); font-size:42px; font-weight:bold; margin-top:5px; text-shadow: 0 0 20px rgba(0,243,255,0.3);">78.4%</div>
                </div>
            </div>
            
            <div style="background:var(--bg-card); padding:25px; border:1px solid var(--border); height:350px;">
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>MATCH ANALYZER</h1></div>
            
            <div style="text-align:center;">
                <button class="btn-analyze" onclick="generujTiket()">SPUSTIŤ ANALÝZU</button>
            </div>

            <div id="loading" style="display:none; text-align:center; color:var(--primary); margin-top: 50px;">
                <h2>⚡ SŤAHUJEM DÁTA...</h2>
            </div>

            <div id="ticket-output"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>HISTÓRIA</h1></div>
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
                        label: 'Bankroll',
                        data: [2100, 2150, 2120, 2250, 2300, 2380, 2450],
                        borderColor: '#00f3ff',
                        backgroundColor: (ctx) => {
                            const grad = ctx.chart.ctx.createLinearGradient(0,0,0,300);
                            grad.addColorStop(0, 'rgba(0, 243, 255, 0.2)');
                            grad.addColorStop(1, 'rgba(0, 243, 255, 0)');
                            return grad;
                        },
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 4,
                        pointBackgroundColor: '#000',
                        pointBorderColor: '#00f3ff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: '#1e2a3b' }, ticks: { color: '#6b8c9e' } },
                        x: { grid: { display: false }, ticks: { color: '#6b8c9e' } }
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
                        <div class="match-header">
                            <div class="team-box">
                                <div class="team-name">${m.domaci}</div>
                                <div class="team-meta">HOME</div>
                                <div class="form-dots">${dots(m.stats.forma_domaci)}</div>
                            </div>
                            <div class="vs-circle">VS</div>
                            <div class="team-box">
                                <div class="team-name">${m.hostia}</div>
                                <div class="team-meta">AWAY</div>
                                <div class="form-dots">${dots(m.stats.forma_hostia)}</div>
                            </div>
                        </div>

                        <div class="stats-grid">
                            <div class="left-panel">
                                
                                <div class="stat-row">
                                    <div class="stat-header">
                                        <span>ÚTOČNÁ SILA (xG)</span>
                                        <span>${m.stats.utok_domaci}% vs ${m.stats.utok_hostia}%</span>
                                    </div>
                                    <div class="bar-container">
                                        <div class="bar-home" style="width:${m.stats.utok_domaci}%"></div>
                                        <div class="bar-away" style="width:${m.stats.utok_hostia}%"></div>
                                    </div>
                                </div>

                                <div class="stat-row">
                                    <div class="stat-header">
                                        <span>PEVNOSŤ OBRANY</span>
                                        <span>${m.stats.obrana_domaci}% vs ${m.stats.obrana_hostia}%</span>
                                    </div>
                                    <div class="bar-container">
                                        <div class="bar-home" style="width:${m.stats.obrana_domaci}%"></div>
                                        <div class="bar-away" style="width:${m.stats.obrana_hostia}%"></div>
                                    </div>
                                </div>

                                <div style="margin-top:30px;">
                                    <div style="font-size:12px; color:#6b8c9e; font-weight:bold; margin-bottom:5px;">POSLEDNÝ VZÁJOMNÝ ZÁPAS</div>
                                    <div style="color:#fff; font-size:18px;">${m.stats.posledny_zapas}</div>
                                </div>

                                <div style="margin-top:20px;">
                                    <div style="font-size:12px; color:#ff0055; font-weight:bold; margin-bottom:5px;">KĽÚČOVÉ ABSENCIE</div>
                                    <div style="color:#e0f7fa;">${m.stats.zranenia}</div>
                                </div>

                            </div>

                            <div class="right-panel">
                                <div class="ai-prediction">
                                    <div class="conf-label">Dôvera modelu</div>
                                    <div class="confidence">${m.dovera}%</div>
                                    <div style="margin:15px 0; border-top:1px solid rgba(0,243,255,0.3);"></div>
                                    <div class="conf-label">Odporúčaný Tip</div>
                                    <div class="tip-val">${m.tip}</div>
                                    <div style="font-size:18px; color:#00f3ff; font-weight:bold;">Kurz: ${m.kurz}</div>
                                </div>
                                
                                <div style="font-size:14px; line-height:1.6; color:#ccc;">
                                    "<b>${m.analyza_titul}</b>"<br>
                                    ${m.analyza_text}
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

# 3. BACKEND (Rozšírené Štatistiky)
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
            "tip": "United & Over 1.5", "dovera": 88,
            "stats": {
                "forma_domaci": "WWDLW", "forma_hostia": "LLDWL",
                "utok_domaci": 75, "utok_hostia": 25,
                "obrana_domaci": 60, "obrana_hostia": 40,
                "zranenia": "Maguire (Out), Shaw (Quest)",
                "posledny_zapas": "Man Utd 2 - 0 PAOK (2023)"
            },
            "analyza_titul": "Dominancia na Old Trafford",
            "analyza_text": "Amorimova taktika funguje. United majú doma priemer 2.4 xG. PAOK vonku stráca stabilitu."
        },
        {
            "domaci": "Lazio", "hostia": "Porto", "kurz": 2.10, 
            "tip": "BTTS (Obaja gól)", "dovera": 75,
            "stats": {
                "forma_domaci": "WWWWL", "forma_hostia": "WWWWW",
                "utok_domaci": 60, "utok_hostia": 40,
                "obrana_domaci": 45, "obrana_hostia": 55,
                "zranenia": "Žiadne významné absencie",
                "posledny_zapas": "Lazio 2 - 2 Porto (2022)"
            },
            "analyza_titul": "Otvorená prestrelka",
            "analyza_text": "Porto skóruje v každom zápase. Lazio doma hrá nátlakovo. Očakávame góly na oboch stranách."
        }
    ]

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): 
    return {"status": "ok"}
