from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - ULTRA PRO VERZIA
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0c10; color: #c5c6c7; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 22px; font-weight: 800; color: #66fcf1; margin-bottom: 50px; text-transform: uppercase; letter-spacing: 3px; text-align: center; border-bottom: 2px solid #66fcf1; padding-bottom: 20px;}
        .menu-item { padding: 15px; margin-bottom: 10px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; display: flex; align-items: center; gap: 15px; }
        .menu-item:hover, .menu-item.active { background-color: #1a1a1a; color: #fff; border-left: 4px solid #66fcf1; }
        
        /* Main Content */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: #0b0c10; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .header h1 { margin: 0; color: #fff; font-size: 28px; font-weight: 700; }
        
        /* Tlačidlo */
        .btn-analyze { 
            background: #66fcf1; border: none; padding: 18px 50px; 
            font-size: 18px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; 
            box-shadow: 0 0 25px rgba(102, 252, 241, 0.4); transition: transform 0.2s;
            display: block; margin: 0 auto 40px auto; letter-spacing: 1px;
        }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }

        /* KARTA ZÁPASU (Advanced) */
        .match-card { 
            background: #151b24; border-radius: 16px; margin-bottom: 30px; overflow: hidden; 
            border: 1px solid #2c3e50; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            animation: slideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
        }
        
        .match-header { 
            background: linear-gradient(90deg, #0f141a 0%, #1a222e 100%); 
            padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; 
            border-bottom: 1px solid #2c3e50;
        }
        .teams-title { font-size: 22px; font-weight: 700; color: white; }
        .match-meta { font-size: 14px; color: #66fcf1; font-weight: bold; background: rgba(102, 252, 241, 0.1); padding: 5px 15px; border-radius: 20px;}
        
        .match-body { padding: 30px; display: flex; gap: 40px; flex-wrap: wrap; }
        
        /* Stĺpce */
        .col-left { flex: 1; min-width: 300px; border-right: 1px solid #2c3e50; padding-right: 30px; }
        .col-right { flex: 1; min-width: 300px; }

        /* Štatistiky - Forma */
        .form-box { display: flex; gap: 5px; margin-top: 5px; }
        .form-badge { width: 25px; height: 25px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: black; }
        .win { background: #2ecc71; }
        .draw { background: #f1c40f; }
        .loss { background: #e74c3c; }

        /* Progress Bary */
        .stat-group { margin-bottom: 20px; }
        .stat-label { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; color: #888; }
        .progress-bg { height: 8px; background: #222; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: #66fcf1; border-radius: 4px; }

        /* Sekcia Analýzy */
        .analysis-section h4 { color: #66fcf1; margin: 0 0 15px 0; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; }
        .analysis-text { font-size: 15px; line-height: 1.6; color: #dcdcdc; }
        .analysis-list { list-style: none; padding: 0; margin-top: 15px; }
        .analysis-list li { margin-bottom: 8px; padding-left: 20px; position: relative; color: #aaa; }
        .analysis-list li::before { content: "•"; color: #66fcf1; position: absolute; left: 0; font-weight: bold; }

        /* AI Prediction Box */
        .ai-box { 
            background: rgba(102, 252, 241, 0.05); padding: 20px; border-radius: 12px; 
            border: 1px solid rgba(102, 252, 241, 0.2); display: flex; align-items: center; justify-content: space-between;
            margin-top: 20px;
        }
        .ai-tip { font-size: 24px; font-weight: 800; color: #fff; }
        .ai-confidence { background: #66fcf1; color: #000; padding: 5px 15px; border-radius: 5px; font-weight: bold; }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

        /* Graf Kontajner */
        .chart-box { background: #151b24; padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; height: 350px; }
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
            <div class="header"><h1>Vitaj späť, Trader.</h1></div>
            
            <div style="display:flex; gap:20px; margin-bottom: 30px;">
                <div style="background:#151b24; padding:25px; flex:1; border-radius:16px; border:1px solid #2c3e50;">
                    <h3 style="color:#888; font-size:14px; margin-top:0;">DNEŠNÝ POTENCIÁL</h3>
                    <h1 style="color:#fff; font-size:36px; margin:10px 0;">3 Zápasy</h1>
                    <small style="color:#66fcf1">AI našla vysokú hodnotu (Value)</small>
                </div>
                <div style="background:#151b24; padding:25px; flex:1; border-radius:16px; border:1px solid #2c3e50;">
                    <h3 style="color:#888; font-size:14px; margin-top:0;">BANKROLL (Simulácia)</h3>
                    <h1 style="color:#fff; font-size:36px; margin:10px 0;">€2,450.00</h1>
                    <small style="color:#2ecc71">▲ +12.5% tento týždeň</small>
                </div>
            </div>
            
            <div class="chart-box">
                <h3 style="color:#fff; margin-top:0;">Vývoj Zisku</h3>
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>Deep AI Analysis</h1></div>
            
            <div style="text-align:center; margin-bottom:40px;">
                <p style="color:#888; margin-bottom:20px;">Spusti hĺbkový sken zápasov. AI analyzuje formu, xG, zranenia a pohyby kurzov.</p>
                <button class="btn-analyze" onclick="generujTiket()">SPUSTIŤ SKENOVANIE</button>
            </div>

            <div id="loading" style="display:none; text-align:center; color:#66fcf1; margin-top: 50px;">
                <h2 style="font-weight:300;">⏳ Analyzujem milióny dátových bodov...</h2>
                <p>Pripravujem report...</p>
            </div>

            <div id="ticket-output"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>Výkonnosť Modelu</h1></div>
            <p>História posledných AI predikcií.</p>
            <div class="match-card">
                <div class="match-header"><div class="teams-title">Včerajší Výkon</div></div>
                <div class="match-body"><p style="color:#aaa;">Načítavam dáta...</p></div>
            </div>
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
                        borderColor: '#66fcf1',
                        backgroundColor: (context) => {
                            const ctx = context.chart.ctx;
                            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
                            gradient.addColorStop(0, 'rgba(102, 252, 241, 0.3)');
                            gradient.addColorStop(1, 'rgba(102, 252, 241, 0)');
                            return gradient;
                        },
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#111',
                        pointBorderColor: '#66fcf1',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: '#2c3e50' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888' } }
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
                    // Generovanie guličiek formy
                    const formGen = (formString) => {
                        let badges = '';
                        for (let char of formString) {
                            let cl = char === 'W' ? 'win' : (char === 'L' ? 'loss' : 'draw');
                            let txt = char === 'W' ? 'V' : (char === 'L' ? 'P' : 'R');
                            badges += `<div class="form-badge ${cl}">${txt}</div>`;
                        }
                        return badges;
                    };

                    html += `
                    <div class="match-card">
                        <div class="match-header>
                        <div class="teams-title">${m.domaci} <span style="color:#888; font-size:16px;">vs</span> ${m.hostia}</div>
                            <div class="match-meta">Kurz: ${m.kurz}</div>
                        </div>
                        <div class="match-body">
                            
                            <div class="col-left">
                                <div class="stat-group">
                                    <div class="stat-label"><span>Forma (Posledných 5)</span></div>
                                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                                        <div style="display:flex; flex-direction:column; gap:5px;">
                                            <small>${m.domaci}</small>
                                            <div class="form-box">${formGen(m.stats.forma_domaci)}</div>
                                        </div>
                                        <div style="display:flex; flex-direction:column; gap:5px; align-items:flex-end;">
                                            <small>${m.hostia}</small>
                                            <div class="form-box">${formGen(m.stats.forma_hostia)}</div>
                                        </div>
                                    </div>
                                </div>

                                <div class="stat-group">
                                    <div class="stat-label"><span>Sila Útoku (xG Power)</span><span>${m.stats.utok_domaci}% vs ${m.stats.utok_hostia}%</span></div>
                                    <div style="display:flex; gap:5px;">
                                        <div class="progress-bg" style="flex:1"><div class="progress-fill" style="width:${m.stats.utok_domaci}%"></div></div>
                                        <div class="progress-bg" style="flex:1"><div class="progress-fill" style="width:${m.stats.utok_hostia}%; background:#e74c3c;"></div></div>
                                    </div>
                                </div>

                                <div class="stat-group">
                                    <div class="stat-label"><span>Absencie (Zranenia)</span></div>
                                    <p style="color:#e74c3c; font-size:13px; margin:0;">${m.stats.zranenia}</p>
                                </div>
                            </div>

                            <div class="col-right">
                                <div class="analysis-section">
                                    <h4>🧠 AI Deep Dive Analýza</h4>
                                    <p class="analysis-text">${m.analyza_text}</p>
                                    
                                    <ul class="analysis-list">
                                        ${m.analyza_body.map(bod => `<li>${bod}</li>`).join('')}
                                    </ul>

                                    <div class="ai-box">
                                        <div>
                                            <div style="font-size:12px; color:#888; text-transform:uppercase;">Odporúčaný Tip</div>
                                            <div class="ai-tip">${m.tip}</div>
                                        </div>
                                        <div style="text-align:right;">
                                            <div style="font-size:12px; color:#888;">Dôvera</div>
                                            <div class="ai-confidence">${m.dovera}%</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                    `;
                });
                out.innerHTML = html;
            } catch(e) { load.style.display = 'none'; alert("Chyba spojenia."); }
        }
    </script>
</body>
</html>
"""

# 3. BACKEND (TOTO JE TO OPRAVENÉ MIESTO)
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
    # TOTO SÚ TIE "ULTRA DÁTA", KTORÉ UVIDÍŠ V GRAFIKE.
    return [
        {
            "domaci": "Manchester United", "hostia": "PAOK", "kurz": 1.45, 
            "tip": "Výhra United & Over 1.5", "dovera": 88,
            "stats": {
                "forma_domaci": "WWDLW", "forma_hostia": "LLDWL",
                "utok_domaci": 82, "utok_hostia": 40,
                "zranenia": "Man Utd: Maguire (Otázny), Shaw (Out)"
            },
            "analyza_text": "United pod novým trénerom Amorimom doma dominuje. Old Trafford je pevnosť, zatiaľ čo PAOK vonku v Európe trpí.",
            "analyza_body": [
                "United má priemer 2.1 xG na domáci zápas.",
                "PAOK inkasoval v 4 z 5 posledných zápasov.",
                "Motivácia domácich potvrdiť postup."
            ]
        },
        {
            "domaci": "Lazio Rím", "hostia": "FC Porto", "kurz": 2.10, 
            "tip": "Obaja dajú gól (BTTS)", "dovera": 75,
            "stats": {
                "forma_domaci": "WWWWL", "forma_hostia": "WWWWW",
                "utok_domaci": 78, "utok_hostia": 85,
                "zranenia": "Lazio: Immobile (lavička), Porto: Žiadne"
            },
            "analyza_text": "Súboj dvoch ofenzívne ladených tímov. Porto má smrtiacu formu, ale v Taliansku sa hrá ťažko. Očakávame góly na oboch stranách.",
            "analyza_body": [
                "Lazio skórovalo v 90% domácich zápasov.",
                "Porto má sériu 7 výhier v rade.",
                "Obrany oboch tímov robia chyby pod tlakom."
            ]
        }
    ]

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): 
    return {"status": "ok"}
