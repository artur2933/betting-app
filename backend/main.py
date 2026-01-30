from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from pydantic import BaseModel
import random

app = FastAPI()

# --- MOCK DATABÁZA (Aby všetko fungovalo hneď) ---
MATCH_DATABASE = [
    {
        "domaci": "Man City", "hostia": "Sheffield", "kurz": 1.18, "tip": "Výhra Domácich", "risk": 1, "liga": "Premier League",
        "stats": {"utok_domaci": 88, "utok_hostia": 20, "obrana_domaci": 70, "obrana_hostia": 30, "forma_domaci": "WWWWW", "forma_hostia": "LLLDL", "zranenia": "De Bruyne (Out)"},
        "analyza": "City doma drví súperov. Sheffield má najhoršiu obranu v lige."
    },
    {
        "domaci": "Real Madrid", "hostia": "Almeria", "kurz": 1.25, "tip": "Výhra Domácich", "risk": 1, "liga": "La Liga",
        "stats": {"utok_domaci": 85, "utok_hostia": 30, "obrana_domaci": 75, "obrana_hostia": 25, "forma_domaci": "WDWWW", "forma_hostia": "LLLLL", "zranenia": "Alaba (Out)"},
        "analyza": "Real potrebuje body na titul. Almeria vonku ešte nevyhrala."
    },
    {
        "domaci": "Bayern", "hostia": "Mainz", "kurz": 1.30, "tip": "Výhra + Over 2.5", "risk": 1, "liga": "Bundesliga",
        "stats": {"utok_domaci": 90, "utok_hostia": 40, "obrana_domaci": 60, "obrana_hostia": 40, "forma_domaci": "WLWWW", "forma_hostia": "LDLDL", "zranenia": "Gnabry (Quest)"},
        "analyza": "Kane je vo forme. Očakávame gólové hody v Mníchove."
    },
    {
        "domaci": "Arsenal", "hostia": "Chelsea", "kurz": 1.95, "tip": "Výhra Domácich", "risk": 2, "liga": "Premier League",
        "stats": {"utok_domaci": 75, "utok_hostia": 65, "obrana_domaci": 70, "obrana_hostia": 50, "forma_domaci": "WWDLW", "forma_hostia": "WLDLW", "zranenia": "Saka (Fit)"},
        "analyza": "Londýnske derby. Arsenal je doma silnejší, Chelsea hľadá identitu."
    },
    {
        "domaci": "Dortmund", "hostia": "Leipzig", "kurz": 2.45, "tip": "BTTS (Obaja gól)", "risk": 2, "liga": "Bundesliga",
        "stats": {"utok_domaci": 80, "utok_hostia": 82, "obrana_domaci": 50, "obrana_hostia": 55, "forma_domaci": "DWWLD", "forma_hostia": "WWWWL", "zranenia": "Reus (Bench)"},
        "analyza": "Oba tímy hrajú ofenzívne. Štatistiky ukazujú 90% šancu na góly."
    },
    {
        "domaci": "Luton", "hostia": "Liverpool", "kurz": 6.50, "tip": "Prekvapenie 1X", "risk": 3, "liga": "Premier League",
        "stats": {"utok_domaci": 40, "utok_hostia": 85, "obrana_domaci": 40, "obrana_hostia": 60, "forma_domaci": "LLWDL", "forma_hostia": "WWWWW", "zranenia": "Salah (Out)"},
        "analyza": "Liverpool bez Salaha a s unavenou zostavou. Luton doma hryzie."
    }
]

# 2. HTML GRAFIKA - PREMIUM GOLD & NAVY (INTEGROVANÁ)
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
        .logo { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 40px; display:flex; align-items:center; gap:10px; }
        .logo span { color: var(--accent); }
        
        .menu-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; margin-top: 20px; }
        .menu-item { padding: 14px; margin-bottom: 8px; cursor: pointer; border-radius: 8px; color: var(--text-muted); font-weight: 600; transition: 0.2s; font-size: 15px; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background: var(--accent); color: #000; }
        
        /* MAIN CONTENT */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: var(--bg-body); }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .header h1 { margin: 0; font-size: 28px; font-weight: 800; color: #fff; }

        /* TLAČIDLÁ */
        .btn-analyze { 
            background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
            border: none; padding: 15px 40px; width: 100%;
            font-size: 16px; font-weight: 800; color: #fff; border-radius: 12px;
            cursor: pointer; transition: all 0.3s; margin-top: 20px;
            box-shadow: 0 10px 30px rgba(251, 191, 36, 0.2);
            text-transform: uppercase; letter-spacing: 1px;
        }
        .btn-analyze:hover { transform: translateY(-2px); box-shadow: 0 20px 40px rgba(251, 191, 36, 0.4); }

        /* --- KARTA ZÁPASU (Detailná s grafmi) --- */
        .match-card { 
            background: var(--bg-card); border-radius: 16px; margin-bottom: 30px; 
            border: 1px solid #334155; overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            animation: slideUp 0.5s ease;
        }

        .card-header { padding: 20px; background: rgba(0,0,0,0.2); border-bottom: 1px solid #334155; display: flex; justify-content: space-between; }
        .league-badge { background: #334155; color: #fff; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }

        .match-teams { padding: 30px 20px; display: flex; justify-content: center; align-items: center; gap: 30px; }
        .team-name { font-size: 24px; font-weight: 800; color: #fff; display: block; text-align: center; width: 40%; }
        .vs { width: 40px; height: 40px; background: var(--accent); color: #000; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; }

        .data-grid { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid #334155; }
        .col-stats { padding: 25px; border-right: 1px solid #334155; }
        .col-ai { padding: 25px; background: linear-gradient(180deg, rgba(251, 191, 36, 0.05) 0%, rgba(0,0,0,0) 100%); }

        /* Kruhové Grafy */
        .circles-container { display: flex; justify-content: space-around; margin-bottom: 20px; }
        .pie { width: 60px; height: 60px; border-radius: 50%; background: conic-gradient(var(--accent) var(--p), #334155 0); display: flex; align-items: center; justify-content: center; }
        .pie span { width: 50px; height: 50px; background: var(--bg-card); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #fff; font-size: 12px; }
        .circle-label { font-size: 10px; color: var(--text-muted); text-align: center; margin-top: 5px; font-weight: bold; }

        /* Forma */
        .form-row { display: flex; justify-content: center; gap: 5px; margin-top: 15px; }
        .dot { width: 8px; height: 8px; border-radius: 2px; }
        .w { background: var(--success); } .d { background: var(--accent); } .l { background: var(--danger); }

        /* AI Text */
        .ai-title { color: var(--accent); font-weight: bold; font-size: 11px; margin-bottom: 5px; text-transform: uppercase; }
        .ai-main-tip { font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 10px; }
        .ai-text { font-size: 13px; line-height: 1.5; color: #cbd5e1; }

        /* --- TIKET DŇA (Papierový vzhľad) --- */
        .ticket-slip {
            background: #fff; color: #000; border-radius: 12px; max-width: 600px; margin: 0 auto;
            box-shadow: 0 0 40px rgba(251, 191, 36, 0.2); overflow: hidden; animation: slideUp 0.5s ease;
        }
        .slip-header { background: var(--accent); padding: 20px; text-align: center; font-weight: 900; font-size: 22px; text-transform: uppercase; }
        .slip-body { padding: 25px; }
        .slip-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #ccc; padding: 15px 0; }
        .slip-row:last-child { border-bottom: none; }
        .slip-total { background: #f1f5f9; padding: 20px; display: flex; justify-content: space-between; align-items: center; font-weight: 900; font-size: 20px; }

        /* --- OVLÁDACIE PRVKY --- */
        .custom-box { background: var(--bg-card); padding: 30px; border-radius: 16px; border: 1px solid #334155; max-width: 800px; margin: 0 auto; }
        select { width: 100%; padding: 15px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 8px; font-size: 16px; margin-bottom: 20px; }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        .chart-container { background: var(--bg-card); padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 30px; height: 300px; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">BET<span>PRO</span></div>
        
        <div class="menu-label">Hlavné</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="loadTiketDna(this)">🎯 Tiket Dňa</div>
        
        <div class="menu-label">Nástroje</div>
        <div class="menu-item" onclick="showPage('custom-gen', this)">🛠️ Vlastný Generátor</div>
        <div class="menu-item" onclick="showPage('scanner', this)">🚀 VIP Scanner</div>
        
        <div class="menu-label">Dáta</div>
        <div class="menu-item" onclick="showPage('results-page', this)">📊 Výsledky</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Prehľad</h1></div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom: 30px;">
                <div style="background:var(--bg-card); padding:25px; border-radius:12px; border:1px solid #334155;">
                    <div style="color:var(--text-muted); font-size:12px; font-weight:bold;">BANKROLL</div>
                    <div style="color:#fff; font-size:36px; font-weight:800;">€2,450.00</div>
                    <div style="color:var(--success); font-size:14px; font-weight:bold;">▲ +12.5%</div>
                </div>
                <div style="background:var(--bg-card); padding:25px; border-radius:12px; border:1px solid #334155;">
                    <div style="color:var(--text-muted); font-size:12px; font-weight:bold;">ÚSPEŠNOSŤ TIKETOV</div>
                    <div style="color:var(--accent); font-size:36px; font-weight:800;">78.4%</div>
                </div>
            </div>
            <div class="chart-container"><canvas id="profitChart"></canvas></div>
        </div>

        <div id="ticket-day" class="page">
            <div class="header"><h1>🔥 Tiket Dňa (Safe)</h1></div>
            <div id="tiket-dna-result"></div>
        </div>

        <div id="custom-gen" class="page">
            <div class="header"><h1>⚙️ Nastav si tiket</h1></div>
            <div class="custom-box">
                <label style="color:#94a3b8; font-weight:bold; display:block; margin-bottom:10px;">RIZIKO</label>
                <select id="riskLevel">
                    <option value="1">🟢 Nízke (Favoriti)</option>
                    <option value="2">🟡 Stredné (Value)</option>
                    <option value="3">🔴 Vysoké (Prekvapenia)</option>
                </select>

                <label style="color:#94a3b8; font-weight:bold; display:block; margin-bottom:10px;">POČET ZÁPASOV</label>
                <select id="matchCount">
                    <option value="1">1 Zápas</option>
                    <option value="2">2 Zápasy</option>
                    <option value="3">3 Zápasy</option>
                </select>

                <label style="color:#94a3b8; font-weight:bold; display:block; margin-bottom:10px;">LIGA</label>
                <select id="leagueSelect">
                    <option value="all">Všetky</option>
                    <option value="Premier League">Premier League</option>
                    <option value="La Liga">La Liga</option>
                    <option value="Bundesliga">Bundesliga</option>
                </select>

                <button class="btn-analyze" onclick="generujVlastny()">Vygenerovať</button>
            </div>
            <div id="custom-output" style="margin-top:40px;"></div>
        </div>

        <div id="scanner" class="page">
            <div class="header"><h1>Celkový Prehľad Trhu</h1></div>
            <div style="text-align:center; margin-bottom:30px;">
                <button class="btn-analyze" style="width:auto; padding:15px 50px;" onclick="generujScanner()">Načítať Všetko</button>
            </div>
            <div id="scanner-output"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>História</h1></div>
            <p style="color:#666">Žiadne dáta.</p>
        </div>

    </div>

    <script>
        // Chart
        document.addEventListener("DOMContentLoaded", function() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'],
                    datasets: [{
                        label: 'Zisk', data: [2100, 2150, 2120, 2250, 2300, 2380, 2450],
                        borderColor: '#fbbf24', backgroundColor: 'rgba(251, 191, 36, 0.1)', fill: true
                    }]
                },
                options: { plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#334155' } }, x: { grid: { display: false } } } }
            });
        });

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            if(el) { document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active')); el.classList.add('active'); }
            document.getElementById(id).classList.add('active');
        }

        // TIKET DŇA
        async function loadTiketDna(el) {
            showPage('ticket-day', el);
            const div = document.getElementById('tiket-dna-result');
            div.innerHTML = '<p style="text-align:center; color:#fbbf24">Generujem...</p>';
            const res = await fetch('/api/tiket-dna');
            const data = await res.json();
            
            let rows = '';
            let total = 1;
            data.forEach(m => {
                total *= m.kurz;
                rows += `<div class="slip-row"><div><b>${m.domaci} - ${m.hostia}</b><br><span style="font-size:12px; color:#555">${m.tip}</span></div><div style="font-weight:bold;">${m.kurz}</div></div>`;
            });

            div.innerHTML = `
            <div class="ticket-slip">
                <div class="slip-header">VIP TIKET DŇA</div>
                <div class="slip-body">${rows}</div>
                <div class="slip-total"><span>Celkový kurz</span><span style="color:#d97706">${total.toFixed(2)}</span></div>
            </div>`;
        }

        // VLASTNÝ GENERÁTOR
        async function generujVlastny() {
            const risk = document.getElementById('riskLevel').value;
            const count = document.getElementById('matchCount').value;
            const league = document.getElementById('leagueSelect').value;
            
            const div = document.getElementById('custom-output');
            div.innerHTML = '<p style="text-align:center; color:#fbbf24">AI hľadá zápasy...</p>';
            
            const res = await fetch(`/api/vlastny-tiket?risk=${risk}&count=${count}&league=${league}`);
            const data = await res.json();
            
            if(data.length === 0) { div.innerHTML = "Žiadne zápasy nenájdené."; return; }
            
            let html = '';
            data.forEach(m => html += renderMatchCard(m));
            div.innerHTML = html;
        }

        // SCANNER
        async function generujScanner() {
            const div = document.getElementById('scanner-output');
            div.innerHTML = '<p style="text-align:center; color:#fbbf24">Načítavam...</p>';
            const res = await fetch('/api/vsetky-zapasy');
            const data = await res.json();
            let html = '';
            data.forEach(m => html += renderMatchCard(m));
            div.innerHTML = html;
        }

        // FUNKCIA NA VYKRESLENIE KARTY (Aby bola rovnaká všade)
        function renderMatchCard(m) {
            const dots = (f) => { let h=''; for(let c of f) h+=`<div class="dot ${c==='W'?'w':(c==='L'?'l':'d')}"></div>`; return h; };
            return `
            <div class="match-card">
                <div class="card-header"><span class="league-badge">${m.liga}</span></div>
                <div class="match-teams">
                    <div style="text-align:center; width:40%;"><span class="team-name">${m.domaci}</span><div class="form-row">${dots(m.stats.forma_domaci)}</div></div>
                    <div class="vs">VS</div>
                    <div style="text-align:center; width:40%;"><span class="team-name">${m.hostia}</span><div class="form-row">${dots(m.stats.forma_hostia)}</div></div>
                </div>
                <div class="data-grid">
                    <div class="col-stats">
                        <div class="circles-container">
                            <div class="circle-wrap"><div class="pie" style="--p:${m.stats.utok_domaci}%"><span>${m.stats.utok_domaci}</span></div><div class="circle-label">ÚTOK (H)</div></div>
                            <div class="circle-wrap"><div class="pie" style="--p:${m.stats.utok_hostia}%"><span>${m.stats.utok_hostia}</span></div><div class="circle-label">ÚTOK (A)</div></div>
                        </div>
                        <div style="text-align:center; color:#ef4444; font-size:12px; margin-top:10px;">🚑 ${m.stats.zranenia}</div>
                    </div>
                    <div class="col-ai">
                        <div class="ai-title">AI ODPORÚČANIE</div>
                        <div class="ai-main-tip">${m.tip} <span style="font-size:14px; color:#fbbf24">(${m.kurz})</span></div>
                        <p class="ai-text">${m.analyza}</p>
                    </div>
                </div>
            </div>`;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

# --- API ENDPOINTS ---

@app.get("/api/vsetky-zapasy")
def get_all():
    return MATCH_DATABASE

@app.get("/api/tiket-dna")
def get_tiket_dna():
    # Vyberieme len RISK 1 (Tutovky)
    safe = [m for m in MATCH_DATABASE if m['risk'] == 1]
    return safe[:3] if len(safe) >=3 else safe

@app.get("/api/vlastny-tiket")
def get_custom(risk: int = 1, count: int = 2, league: str = "all"):
    # 1. Filter podľa rizika
    res = [m for m in MATCH_DATABASE if m['risk'] == risk]
    # 2. Filter podľa ligy
    if league != "all":
        res = [m for m in res if m['liga'] == league]
    
    # Fallback ak nenájde dosť
    if len(res) < count:
        res = [m for m in MATCH_DATABASE if m['risk'] == risk] # Zoberieme aspoň podľa risku z iných líg
    
    return random.sample(res, min(len(res), count))

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
