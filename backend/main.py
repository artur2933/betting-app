from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - PRO VERZIA S GRAFOM (CHART.JS)
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: #c5c6c7; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 260px; background-color: #1f2833; display: flex; flex-direction: column; padding: 20px; border-right: 1px solid #45a29e; }
        .logo { font-size: 24px; font-weight: bold; color: #66fcf1; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 2px; text-align: center; }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 5px; color: #fff; font-weight: 500; transition: 0.3s; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background-color: #45a29e; color: #0b0c10; box-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        
        /* Main Content */
        .main-content { flex: 1; padding: 30px; overflow-y: auto; background: radial-gradient(circle at top, #1f2833 0%, #0b0c10 80%); }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid #45a29e; padding-bottom: 15px; }
        .header h1 { margin: 0; color: #fff; }
        
        /* Tlačidlo */
        .btn-analyze { 
            background: linear-gradient(45deg, #45a29e, #66fcf1); border: none; padding: 15px 40px; 
            font-size: 18px; font-weight: bold; color: #0b0c10; border-radius: 30px; cursor: pointer; 
            box-shadow: 0 0 20px rgba(102, 252, 241, 0.3); transition: transform 0.2s;
            display: block; margin: 0 auto 30px auto;
        }
        .btn-analyze:hover { transform: scale(1.05); }

        /* KARTA ZÁPASU */
        .match-card { 
            background: #1f2833; border-radius: 10px; margin-bottom: 25px; overflow: hidden; 
            border: 1px solid #333; box-shadow: 0 5px 15px rgba(0,0,0,0.5);
            animation: slideUp 0.5s ease;
        }
        .match-header { background: #0b0c10; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #45a29e; }
        .teams { font-size: 20px; font-weight: bold; color: white; }
        .league { font-size: 14px; color: #66fcf1; font-weight: bold; }
        .match-body { padding: 20px; display: flex; gap: 20px; flex-wrap: wrap; }
        .stats-col { flex: 1; min-width: 250px; border-right: 1px solid #333; padding-right: 20px; }
        .stat-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
        .stat-bar { height: 6px; background: #333; border-radius: 3px; overflow: hidden; margin-top: 2px; }
        .stat-fill { height: 100%; background: #66fcf1; }
        .analysis-col { flex: 1.5; min-width: 250px; padding-left: 10px; }
        .prediction-box { background: rgba(69, 162, 158, 0.2); padding: 15px; border-radius: 5px; border-left: 4px solid #66fcf1; margin-bottom: 15px; }
        .prediction-title { color: #66fcf1; font-weight: bold; font-size: 12px; text-transform: uppercase; }
        .prediction-value { font-size: 20px; font-weight: bold; color: white; margin-top: 5px; }
        .reason-text { font-size: 14px; color: #ccc; line-height: 1.6; font-style: italic; }

        /* VÝSLEDKY TABUĽKA */
        .result-row { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #333; align-items: center; }
        .result-row:last-child { border-bottom: none; }
        .status-badge { padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
        .win { background: rgba(0, 255, 136, 0.2); color: #00ff88; border: 1px solid #00ff88; }
        .loss { background: rgba(255, 0, 0, 0.2); color: #ff4444; border: 1px solid #ff4444; }

        /* GRAF KONTAJNER */
        .chart-container {
            background: #151b24; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-top: 20px;
            box-shadow: 0 0 20px rgba(0,0,0,0.3); height: 300px; position: relative;
        }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 Analýza Zápasov</div>
        <div class="menu-item" onclick="showPage('results-page', this)">✅ Výsledky AI</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Prehľad Trhu</h1></div>
            <div style="display:flex; gap:20px;">
                <div style="background:#1f2833; padding:20px; flex:1; border-radius:10px;">
                    <h3>🤖 Úspešnosť AI (Včera)</h3>
                    <h1 style="color:#66fcf1">3 / 4 (75%)</h1>
                    <small style="color:#888">Zisk: +2.45 jednotiek</small>
                </div>
                <div style="background:#1f2833; padding:20px; flex:1; border-radius:10px;">
                    <h3>💰 Celkový Bankroll</h3>
                    <h1 style="color:#66fcf1">€2,450.00</h1>
                    <small style="color:#00ff88">▲ +12% tento týždeň</small>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>AI Analýza & Tipy</h1></div>
            
            <div style="text-align:center; margin-bottom:30px;">
                <p>Klikni a nechaj AI spracovať štatistiky dnešných zápasov.</p>
                <button class="btn-analyze" onclick="generujTiket()">🚀 Skenovať Ponuku</button>
            </div>

            <div id="loading" style="display:none; text-align:center; color:#66fcf1; margin-top: 50px;">
                <h2>⏳ Sťahujem dáta o strelách, držaní lopty a forme...</h2>
                <p>Prosím čakaj, prebieha hĺbková analýza.</p>
            </div>

            <div id="ticket-output"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>Ako sa darilo AI?</h1></div>
            <p style="margin-bottom: 20px;">Prehľad tipov, ktoré náš robot vygeneroval za posledných 24 hodín.</p>
            
            <div class="match-card">
                <div class="match-header"><div class="teams">Včerajšie Tipy</div><div class="league">29. Január</div></div>
                <div style="padding: 0;">
                    <div class="result-row"><div><b>Barcelona vs Osasuna</b><br><small style="color:#aaa">Tip: Barcelona -1.5</small></div><div class="status-badge win">VÝHRA ✅</div></div>
                    <div class="result-row"><div><b>Liverpool vs Chelsea</b><br><small style="color:#aaa">Tip: Remíza</small></div><div class="status-badge loss">PREHRA ❌</div></div>
                    <div class="result-row"><div><b>AC Milan vs Bologna</b><br><small style="color:#aaa">Tip: AC Milan</small></div><div class="status-badge win">VÝHRA ✅</div></div>
                </div>
            </div>
        </div>

    </div>

    <script>
        // Inicializácia Grafu (Chart.js)
        document.addEventListener("DOMContentLoaded", function() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Pon', 'Uto', 'Str', 'Štv', 'Pia', 'Sob', 'Ned'],
                    datasets: [{
                        label: 'Vývoj Zisku (Bankroll)',
                        data: [2100, 2150, 2120, 2250, 2300, 2380, 2450],
                        borderColor: '#66fcf1',
                        backgroundColor: 'rgba(102, 252, 241, 0.1)',
                        borderWidth: 3,
                        tension: 0.4, // Hladká krivka
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: '#333' }, ticks: { color: '#888' } },
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
                    let hp = m.stats.utok_domaci; 
                    let ap = m.stats.utok_hostia;
                    html += `<div class="match-card"><div class="match-header"><div class="teams">${m.domaci} vs ${m.hostia}</div><div class="league">Kurz: ${m.kurz}</div></div><div class="match-body"><div class="stats-col"><div style="color:#888;margin-bottom:10px;font-size:12px;font-weight:bold;">KĽÚČOVÉ ŠTATISTIKY</div><div class="stat-row"><span>Gólový priemer</span><span>${m.stats.goly_priemer}</span></div><div class="stat-row"><span>xG (Očakávané góly)</span><span>${m.stats.xg_data}</span></div><div style="margin-top:15px;"><div class="stat-row"><span>Sila Útoku (Domáci)</span><span>${hp}%</span></div><div class="stat-bar"><div class="stat-fill" style="width:${hp}%"></div></div></div><div style="margin-top:10px;"><div class="stat-row"><span>Sila Útoku (Hostia)</span><span>${ap}%</span></div><div class="stat-bar"><div class="stat-fill" style="width:${ap}%"></div></div></div></div><div class="analysis-col"><div class="prediction-box"><div class="prediction-title">ODPORÚČANÝ TIP</div><div class="prediction-value">${m.tip}</div></div><div class="reason-text">"<b>${m.analyza_titulek}</b>"<br>${m.analyza_text}</div></div></div></div>`;
                });
                out.innerHTML = html;
            } catch(e) { load.style.display = 'none'; alert("Chyba spojenia."); }
        }
    </script>
</body>
</html>
"""

# 3. BACKEND (Simulácia dát)
def get_db():
    db = database.SessionLocal(); try: yield db; finally: db.close()

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

@app.get("/api/generuj-tiket")
def generuj_denny_tiket(db: Session = Depends(get_db)):
    # Dáta pre generátor (zatiaľ demo)
    return [
        {"domaci": "Man Utd", "hostia": "PAOK", "kurz": 1.25, "tip": "Over 2.5", "stats": {"goly_priemer": "2.4 - 0.8", "xg_data": "1.85 vs 0.42", "utok_domaci": 85, "utok_hostia": 30}, "analyza_titulek": "Dominancia", "analyza_text": "United doma strieľa veľa."},
        {"domaci": "Lazio", "hostia": "Porto", "kurz": 1.75, "tip": "BTTS", "stats": {"goly_priemer": "1.8 - 1.9", "xg_data": "1.20 vs 1.35", "utok_domaci": 65, "utok_hostia": 70}, "analyza_titulek": "Otvorený zápas", "analyza_text": "Lazio doma vždy skóruje."},
        {"domaci": "Galatasaray", "hostia": "Tottenham", "kurz": 2.10, "tip": "Over 3.5", "stats": {"goly_priemer": "3.1 - 2.8", "xg_data": "2.40 vs 2.10", "utok_domaci": 90, "utok_hostia": 88}, "analyza_titulek": "Prestrelka", "analyza_text": "Osimhen vs Spurs."}
    ]

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
